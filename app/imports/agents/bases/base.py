import typing as t
from collections import defaultdict
from functools import cached_property, lru_cache
from uuid import uuid4

import pendulum
import redis.lock
from sqlalchemy.dialects.postgresql import insert

import settings
from app import db, models, tasks
from app.feeds import FeedType
from app.imports.exceptions import MIDDataError, MissingMID
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



class IdentifyArgs(t.NamedTuple):
    transaction_id: str
    merchant_identifier_ids: list[int]
    card_token: str


TxType = t.Union[models.SchemeTransaction, models.PaymentTransaction]


@lru_cache(maxsize=2048)
def identify_mids(*mids: str, feed_type: FeedType, provider_slug: str, session: db.Session) -> t.List[int]:
    def find_mids():
        q = session.query(models.MerchantIdentifier)

        if feed_type == FeedType.MERCHANT:
            q = q.join(models.MerchantIdentifier.loyalty_scheme).filter(models.LoyaltyScheme.slug == provider_slug)
        elif feed_type in (FeedType.SETTLED, FeedType.AUTH, FeedType.REFUND):
            q = q.join(models.MerchantIdentifier.payment_provider).filter(models.PaymentProvider.slug == provider_slug)
        else:
            raise ValueError(f"Unsupported feed type: {feed_type}")

        return q.filter(models.MerchantIdentifier.mid.in_(mids)).all()

    merchant_identifiers = db.run_query(
        find_mids,
        session=session,
        read_only=True,
        description=f"find {provider_slug} MID",
    )
    return [mid.id for mid in merchant_identifiers]


@lru_cache(maxsize=2048)
def get_merchant_slug(*mids: str, payment_provider_slug: str) -> str:
    with db.session_scope() as session:

        def find_slug():
            return (
                session.query(models.LoyaltyScheme.slug)
                .distinct()
                .join(models.MerchantIdentifier)
                .join(models.PaymentProvider)
                .filter(models.MerchantIdentifier.mid.in_(mids), models.PaymentProvider.slug == payment_provider_slug)
                .scalar()
            )

        return db.run_query(
            find_slug, session=session, read_only=True, description=f"find merchant slug for mids {mids}"
        )


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

    def to_transaction_fields(self, data: dict) -> t.Union[SchemeTransactionFields, PaymentTransactionFields]:
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
                        models.MerchantIdentifier.mid,
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
        for (location_id, mid) in data:
            location_id_mid_map[location_id].append(mid)
        return location_id_mid_map

    def get_mids(self, data: dict) -> t.List[str]:
        raise NotImplementedError("Override get_mids in your agent.")

    def get_merchant_slug(self, data: dict) -> str:
        mids = self.get_mids(data)
        # we can use self.provider_slug as the payment provider slug as there is no reason to ever call this function
        # in a loyalty import agent.
        return get_merchant_slug(*mids, payment_provider_slug=self.provider_slug)

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
        new: t.List[dict] = []
        for tx in provider_transactions:
            tid = self.get_transaction_id(tx)
            if tid not in seen_tids:
                seen_tids.add(tid)  # we add the transaction ID to avoid duplicates within this file
                new.append(tx)

        self.log.debug(
            f"Found {len(new)} new transactions in import set of {len(provider_transactions)} total transactions."
        )

        return new

    def _identify_mids(self, mids: list[str], session: db.Session) -> t.List[int]:
        ids = identify_mids(*mids, feed_type=self.feed_type, provider_slug=self.provider_slug, session=session)
        if not ids:
            raise MissingMID

        if self.feed_type != FeedType.MERCHANT and len(ids) > 1:
            raise MIDDataError(
                f"{type(self).__name__} is a payment feed agent and must therefore only provide a single MID value per "
                f"transaction. However, the agent mapped this MIDs list: {mids} to these multiple IDs: {ids}. "
                "This indicates an issue with the MIDs loaded into the database. Please ensure that this combination "
                "of MIDs only maps to a single merchant_identifier record.\n"
                "Note, Visa MIDs are given as [MID, VSID]. If this is a Visa issue, ensure that either the MID or the "
                "VSID is loaded, and not both."
            )

        return ids

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
        import_transaction_inserts = []
        transaction_inserts = []

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
                import_transaction_insert, transaction_insert, identify = self._build_inserts(
                    tx_data, match_group, source, session=session
                )
                import_transaction_inserts.append(import_transaction_insert)

                if transaction_insert:
                    transaction_inserts.append(transaction_insert)

                if identify:
                    identify_args.append(identify)
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
                tasks.identify_user_queue.enqueue(tasks.identify_user, feed_type=self.feed_type, **args._asdict())
        elif self.feed_type == FeedType.MERCHANT:
            # merchant imports can go straight to matching/streaming
            tasks.import_queue.enqueue(tasks.import_transactions, match_group)

    def _build_inserts(
        self, tx_data: dict, match_group: str, source: str, *, session: db.Session
    ) -> tuple[dict, t.Optional[dict], t.Optional[IdentifyArgs]]:
        tid = self.get_transaction_id(tx_data)
        mids = self.get_mids(tx_data)

        merchant_identifier_ids = []
        identified = True
        try:
            merchant_identifier_ids.extend(self._identify_mids(mids, session=session))
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
        transaction_insert = None
        identify = None

        if identified:
            transaction_fields = self.to_transaction_fields(tx_data)
            transaction_insert = dict(
                feed_type=self.feed_type,
                status=models.TransactionStatus.IMPORTED,
                merchant_identifier_ids=merchant_identifier_ids,
                transaction_id=tid,
                match_group=match_group,
                **transaction_fields._asdict(),
            )

            if self.feed_type_is_payment:
                if not isinstance(transaction_fields, PaymentTransactionFields):
                    raise self.ImportError(
                        f"{self.provider_slug} agent is configured with a feed type of {self.feed_type}, "
                        f" but provided {type(transaction_fields).__name__} instead of PaymentTransactionFields"
                    )

                identify = IdentifyArgs(
                    transaction_id=tid,
                    merchant_identifier_ids=merchant_identifier_ids,
                    card_token=transaction_fields.card_token,
                )

        return import_transaction_insert, transaction_insert, identify

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
