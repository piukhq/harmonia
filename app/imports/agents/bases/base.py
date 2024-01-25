import typing as t
from collections import defaultdict
from functools import cached_property, lru_cache
from uuid import uuid4

import pendulum
import redis.lock
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql import tuple_

import settings
from app import db, models, tasks
from app.feeds import FeedType
from app.imports.exceptions import MissingMID
from app.prometheus import bink_prometheus
from app.reporting import get_logger
from app.utils import missing_property


class SchemeTransactionFields(t.NamedTuple):
    merchant_slug: str
    payment_provider_slug: str
    transaction_date: pendulum.DateTime
    has_time: bool
    spend_amount: int
    spend_multiplier: int
    spend_currency: str
    first_six: t.Optional[str] = None
    last_four: t.Optional[str] = None
    auth_code: str = ""
    extra_fields: t.Optional[dict] = None


class PaymentTransactionFields(t.NamedTuple):
    merchant_slug: str
    payment_provider_slug: str
    transaction_date: pendulum.DateTime
    has_time: bool
    spend_amount: int
    spend_multiplier: int
    spend_currency: str
    card_token: str
    settlement_key: str
    first_six: t.Optional[str] = None
    last_four: t.Optional[str] = None
    auth_code: str = ""
    approval_code: str = ""
    extra_fields: t.Optional[dict] = None


class IdentifyArgs(t.NamedTuple):
    transaction_id: str
    merchant_identifier_ids: list[int]
    card_token: str


TxType = t.Union[models.SchemeTransaction, models.PaymentTransaction]


@lru_cache(maxsize=2048)
def find_identifiers(
    *identifiers: tuple[models.IdentifierType, str], provider_slug: str, session: db.Session
) -> dict[models.IdentifierType, int]:
    def lookup():
        return (
            session.query(models.MerchantIdentifier)
            .join(models.MerchantIdentifier.payment_provider)
            .filter(models.PaymentProvider.slug == provider_slug)
            .filter(
                tuple_(models.MerchantIdentifier.identifier_type, models.MerchantIdentifier.identifier).in_(identifiers)
            )
            .all()
        )

    merchant_identifiers = db.run_query(
        lookup,
        session=session,
        read_only=True,
        description=f"find {provider_slug} identifier",
    )

    return {mid.identifier_type: mid.id for mid in merchant_identifiers}


@lru_cache(maxsize=2048)
def get_mids_by_location_id(location_id: str, *, scheme_slug: str, payment_slug: str) -> list[str]:
    """
    Find primary MIDs by location ID (store ID.)
    """
    with db.session_scope() as session:

        def get_data():
            return (
                session.query(models.MerchantIdentifier.identifier)
                .join(models.LoyaltyScheme)
                .join(models.PaymentProvider)
                .filter(
                    models.LoyaltyScheme.slug == scheme_slug,
                    models.PaymentProvider.slug == payment_slug,
                    models.MerchantIdentifier.location_id == location_id,
                    models.MerchantIdentifier.identifier_type == models.IdentifierType.PRIMARY,
                )
                .all()
            )

        results = db.run_query(
            get_data,
            session=session,
            read_only=True,
            description=f"find {scheme_slug} MIDs by location ID",
        )

        return [mid[0] for mid in results]


@lru_cache(maxsize=2048)
def get_merchant_slugs(*mids: str, payment_provider_slug: str) -> list[str]:
    with db.session_scope() as session:

        def find_slugs():
            return (
                session.query(models.LoyaltyScheme.slug)
                .distinct()
                .join(models.MerchantIdentifier)
                .join(models.PaymentProvider)
                .filter(
                    models.MerchantIdentifier.identifier.in_([identifier for _, identifier in mids]),
                    models.PaymentProvider.slug == payment_provider_slug,
                )
                .all()
            )

        results = db.run_query(
            find_slugs, session=session, read_only=True, description=f"find merchant slugs for identifiers {mids}"
        )

        return [result[0] for result in results]


class FeedTypeError(Exception):
    ...


class BaseAgent:
    class ImportError(Exception):
        pass

    def __init__(self) -> None:
        self.log = get_logger(f"import-agent.{self.provider_slug}")
        self.bink_prometheus = bink_prometheus

    @property
    def provider_slug(self) -> str:
        return missing_property(type(self), "provider_slug")

    @property
    def feed_type(self) -> FeedType:
        return missing_property(type(self), "feed_type")

    @property
    def feed_type_is_payment(self) -> bool:
        return self.feed_type in [FeedType.AUTH, FeedType.SETTLED, FeedType.REFUND]

    def run(self):
        raise NotImplementedError(
            "Override the run method in your agent to act as the main entry point into the import process."
        )

    def to_transaction_fields(self, data: dict) -> list[SchemeTransactionFields] | list[PaymentTransactionFields]:
        raise NotImplementedError("Override to_transaction_fields in your agent.")

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        raise NotImplementedError("Override get_transaction_id in your agent.")

    @cached_property
    def location_id_mid_map(self) -> t.DefaultDict[str, t.List[str]]:
        with db.session_scope() as session:

            def get_data():
                return (
                    session.query(
                        models.MerchantIdentifier.location_id,
                        models.MerchantIdentifier.identifier,
                    )
                    .join(models.LoyaltyScheme)
                    .filter(models.LoyaltyScheme.slug == self.provider_slug)
                    .filter(models.MerchantIdentifier.location_id.isnot(None))
                    .distinct()
                )

            data = db.run_query(
                get_data,
                session=session,
                read_only=True,
                description=f"find {self.provider_slug} MIDs by location ID",
            )

        location_id_mid_map = defaultdict(list)
        for location_id, mid in data:
            location_id_mid_map[location_id].append(mid)
        return location_id_mid_map

    def get_primary_mids(self, data: dict) -> list[str]:
        raise NotImplementedError("Override get_primary_mids in your agent.")

    def get_secondary_mid(self, data: dict) -> str | None:
        return None

    def get_psimi(self, data: dict) -> str | None:
        return None

    def _all_identifiers(self, data: dict) -> list[tuple[models.IdentifierType, str]]:
        identifiers = [(models.IdentifierType.PRIMARY, mid) for mid in self.get_primary_mids(data)]

        if secondary_mid := self.get_secondary_mid(data):
            identifiers.append((models.IdentifierType.SECONDARY, secondary_mid))

        if psimi := self.get_psimi(data):
            identifiers.append((models.IdentifierType.PSIMI, psimi))

        return identifiers

    def get_merchant_slugs(self, data: dict) -> list[str]:
        if self.feed_type == FeedType.MERCHANT:
            raise FeedTypeError("get_merchant_slugs should only be called from payment agents")

        identifiers = self._all_identifiers(data)
        return get_merchant_slugs(*identifiers, payment_provider_slug=self.provider_slug)

    @staticmethod
    def pendulum_parse(date_time: str, *, tz: str = "GMT") -> pendulum.DateTime:
        # pendulum 2.1.0 has a type hint bug that suggests `parse` returns a string.
        # we can remove this fix when the bug is resolved.
        # https://github.com/sdispater/pendulum/pull/452
        return pendulum.parse(date_time, tz=tz)  # type: ignore

    def _find_new_transactions(self, provider_transactions: t.List[dict], *, session: db.Session) -> t.List[dict]:
        """Returns a subset of provider_transactions whose transaction IDs do not appear in the DB yet."""
        tids_in_set = {self.get_transaction_id(t) for t in provider_transactions}

        # this result set can be very large, so limit the yield amount
        # local testing indicates that a yield size of 100k results in roughly 120 MB memory used for this process.
        # TODO: make this a global setting & scale based on model size?
        yield_per = 100000

        seen_tids = {
            row[0]
            for row in db.run_query(
                lambda: session.query(models.ImportTransaction.transaction_id)
                .distinct()
                .yield_per(yield_per)
                .filter(
                    models.ImportTransaction.provider_slug == self.provider_slug,
                    models.ImportTransaction.transaction_id.in_(tids_in_set),
                    models.ImportTransaction.feed_type == self.feed_type,
                ),
                session=session,
                read_only=True,
                description=f"find duplicated {self.provider_slug} import transactions",
            )
            if row[0] in tids_in_set
        }

        # Use list of duplicate transaction IDs to find new transactions.
        new: list[dict] = []
        for tx in provider_transactions:
            tid = self.get_transaction_id(tx)
            if tid not in seen_tids:
                seen_tids.add(tid)  # we add the transaction ID to avoid duplicates within this file
                new.append(tx)

        self.log.debug(
            f"Found {len(new)} new transactions in import set of {len(provider_transactions)} total transactions."
        )

        return new

    # This is not currently utilised by merchant transactions
    def _identify_mids(self, mids: list[tuple[models.IdentifierType, str]], session: db.Session) -> list[int]:
        # Queries the MerchantIdentifier table for all possible mid matches in dictionary form identifier_type: mid_id,
        # then sorts the dictionary per identifier_type (enum values) and returns the mid_id of the first element
        ids = find_identifiers(*mids, provider_slug=self.provider_slug, session=session)
        if not ids:
            raise MissingMID

        # accumulate into identifier_type: identifiers
        identifiers_by_type: defaultdict[models.IdentifierType, list[int]] = defaultdict(list)
        for identifier_type, identifier in ids.items():
            identifiers_by_type[identifier_type].append(identifier)

        # sort by identifier type
        sorted_identifiers = sorted(identifiers_by_type.items(), key=lambda x: x[0].value)

        # return identifiers of the best identifier type available
        return sorted_identifiers[0][1]

    def _import_transactions(
        self, provider_transactions: t.List[dict], *, session: db.Session, source: str
    ) -> t.Generator[None, None, int]:
        """
        Imports the given list of deserialized provider transactions.
        Creates ImportTransaction instances in the database, and enqueues the
        transaction data to be matched.
        """
        new = self._find_new_transactions(provider_transactions, session=session)
        if not new:
            self.log.debug(f'No new transactions found in source "{source}", exiting early.')
            return 0

        # NOTE: it may be worth limiting the batch size if files get any larger than 10k transactions.
        import_transaction_inserts: list[dict] = []
        transaction_inserts: list[dict] = []

        # user ID requests to enqueue after import
        identify_args: list[IdentifyArgs] = []

        # generate a match group ID
        match_group = uuid4().hex

        for tx_data in new:
            tid = self.get_transaction_id(tx_data)

            # attempt to lock this transaction id.
            lock_key = f"{settings.REDIS_KEY_PREFIX}:import-lock:{self.provider_slug}:{tid}"
            lock: redis.lock.Lock = db.redis.lock(lock_key, timeout=300)
            if not lock.acquire(blocking=False):
                self.log.warning(f"Transaction {lock_key} is already locked. Skipping.")
                continue

            try:
                import_transaction_insert, new_transaction_inserts, identifies = self._build_inserts(
                    tx_data, match_group, source, session=session
                )
                import_transaction_inserts.append(import_transaction_insert)

                transaction_inserts.extend(new_transaction_inserts)
                identify_args.extend(identifies)
            finally:
                lock.release()

            yield

        self._persist_and_enqueue(import_transaction_inserts, transaction_inserts, identify_args, match_group)

        return len(new)

    def _persist_and_enqueue(
        self,
        import_transaction_inserts: list[dict],
        transaction_inserts: list[dict],
        identify_args: list[IdentifyArgs],
        match_group: str,
    ) -> None:
        if import_transaction_inserts:
            db.engine.execute(
                insert(models.ImportTransaction.__table__).values(import_transaction_inserts).on_conflict_do_nothing()
            )
            self._update_metrics(n_insertions=len(import_transaction_inserts))

        if transaction_inserts:
            db.engine.execute(insert(models.Transaction.__table__).values(transaction_inserts).on_conflict_do_nothing())

        if self.feed_type_is_payment:
            # payment imports need to get identified before they can be matched
            for args in identify_args:
                tasks.identify_user_queue.enqueue(
                    tasks.identify_user, feed_type=self.feed_type, match_group=match_group, **args._asdict()
                )
        elif self.feed_type == FeedType.MERCHANT:
            # merchant imports can go straight to matching/streaming
            tasks.import_queue.enqueue(tasks.import_transactions, match_group)

    def _build_inserts(
        self, tx_data: dict, match_group: str, source: str, *, session: db.Session
    ) -> tuple[dict, list[dict], list[IdentifyArgs]]:
        tid = self.get_transaction_id(tx_data)
        primary_mids = self.get_primary_mids(tx_data)

        merchant_identifier_ids = []
        identified = True
        # We don't identify mids for merchant transactions since some merchants don't know their
        # primary mids and therefore won't import
        if self.feed_type_is_payment:
            try:
                identifiers = self._all_identifiers(tx_data)
                merchant_identifier_ids.extend(self._identify_mids(identifiers, session=session))
            except MissingMID:
                identified = False

        import_transaction_insert = dict(
            transaction_id=tid,
            feed_type=self.feed_type,
            provider_slug=self.provider_slug,
            identified=identified,
            match_group=match_group,
            data=tx_data,
            source=source,
        )
        transaction_inserts = []
        identifies = []

        if identified:
            transaction_fields = self.to_transaction_fields(tx_data)

            for fields in transaction_fields:
                # if an agent yields more than one set of fields, we have to make the transaction ID unique for each set.
                # note that ImportTransaction always uses the original transaction ID rather than this adjusted one.
                # we also only do this for payment agents.
                if len(transaction_fields) > 1 and self.feed_type_is_payment:
                    adjusted_tid = f"{fields.merchant_slug}:{tid}"
                else:
                    adjusted_tid = tid
                
                transaction_inserts.append(
                    dict(
                        feed_type=self.feed_type,
                        status=models.TransactionStatus.IMPORTED,
                        merchant_identifier_ids=merchant_identifier_ids,
                        mids=primary_mids,
                        transaction_id=adjusted_tid,
                        match_group=match_group,
                        **fields._asdict(),
                    )
                )

                if self.feed_type_is_payment:
                    if not isinstance(fields, PaymentTransactionFields):
                        raise self.ImportError(
                            f"{self.provider_slug} agent is configured with a feed type of {self.feed_type}, "
                            f" but provided {type(fields).__name__} instead of PaymentTransactionFields"
                        )

                    identifies.append(
                        IdentifyArgs(
                            transaction_id=adjusted_tid,
                            merchant_identifier_ids=merchant_identifier_ids,
                            card_token=fields.card_token,
                        )
                    )

        return import_transaction_insert, transaction_inserts, identifies

    def _update_metrics(self, n_insertions: int) -> None:
        """
        Update any Prometheus metrics this agent might have
        """
        transaction_type = self.feed_type.name.lower()
        self.bink_prometheus.increment_counter(
            agent=self,
            counter_name="transactions",
            increment_by=n_insertions,
            transaction_type=transaction_type,
            process_type="import",
            slug=self.provider_slug,
        )
