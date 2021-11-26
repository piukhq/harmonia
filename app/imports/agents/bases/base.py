import typing as t
from collections import defaultdict
from functools import cached_property, lru_cache
from uuid import uuid4

import pendulum
import redis.lock

import settings
from app import db, models, tasks
from app.feeds import FeedType
from app.imports.exceptions import MissingMID
from app.prometheus import bink_prometheus
from app.reporting import get_logger
from app.status import status_monitor
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


class IdentifyArgs(t.NamedTuple):
    transaction_id: str
    merchant_identifier_ids: list[int]
    card_token: str


TxType = t.Union[models.SchemeTransaction, models.PaymentTransaction]


@lru_cache(maxsize=2048)
def identify_mid(mid: str, feed_type: FeedType, provider_slug: str, *, session: db.Session) -> t.List[int]:
    def find_mid():
        q = session.query(models.MerchantIdentifier)

        if feed_type == FeedType.MERCHANT:
            q = q.join(models.MerchantIdentifier.loyalty_scheme).filter(models.LoyaltyScheme.slug == provider_slug)
        elif feed_type in (FeedType.SETTLED, FeedType.AUTH):
            q = q.join(models.MerchantIdentifier.payment_provider).filter(models.PaymentProvider.slug == provider_slug)
        else:
            raise ValueError(f"Unsupported feed type: {feed_type}")

        return q.filter(models.MerchantIdentifier.mid == mid).all()

    merchant_identifiers = db.run_query(
        find_mid,
        session=session,
        read_only=True,
        description=f"find {provider_slug} MID",
    )
    return [mid.id for mid in merchant_identifiers]


@lru_cache(maxsize=2048)
def get_merchant_slug(mid: str) -> str:
    with db.session_scope() as session:

        def find_slug():
            return (
                session.query(models.LoyaltyScheme.slug)
                .distinct()
                .join(models.MerchantIdentifier)
                .filter(models.MerchantIdentifier.mid == mid)
                .scalar()
            )

        return db.run_query(find_slug, session=session, read_only=True, description=f"find merchant slug for mid {mid}")


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

    def help(self, session: db.Session) -> str:
        return (
            "This is a new import agent.\n"
            "Implement all the required methods (see agent base classes) "
            "and override this help method to provide specific information."
        )

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
    def storeid_mid_map(self) -> t.DefaultDict[str, t.List[str]]:
        with db.session_scope() as session:

            def get_data():
                return (
                    session.query(
                        models.MerchantIdentifier.store_id,
                        models.MerchantIdentifier.mid,
                    )
                    .join(models.LoyaltyScheme)
                    .filter(models.LoyaltyScheme.slug == self.provider_slug)
                    .filter(models.MerchantIdentifier.store_id.isnot(None))
                    .distinct()
                )

            data = db.run_query(
                get_data,
                session=session,
                read_only=True,
                description=f"find {self.provider_slug} MIDs by store ID",
            )

        storeid_mid_map = defaultdict(list)
        for (store_id, mid) in data:
            storeid_mid_map[store_id].append(mid)
        return storeid_mid_map

    def get_mids(self, data: dict) -> t.List[str]:
        raise NotImplementedError("Override get_mids in your agent.")

    def get_merchant_slug(self, data: dict) -> str:
        mid = self.get_mids(data).pop()
        return get_merchant_slug(mid)

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

    def _identify_mid(self, mid: str, *, session: db.Session) -> t.List[int]:
        mids = identify_mid(mid, self.feed_type, self.provider_slug, session=session)
        if not mids:
            raise MissingMID
        return mids

    def _import_transactions(
        self, provider_transactions: t.List[dict], *, session: db.Session, source: str
    ) -> t.Generator[None, None, int]:
        """
        Imports the given list of deserialized provider transactions.
        Creates ImportTransaction instances in the database, and enqueues the
        transaction data to be matched.
        """
        status_monitor.checkin(self)

        new = self._find_new_transactions(provider_transactions, session=session)

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

        if import_transaction_inserts:
            db.engine.execute(models.ImportTransaction.__table__.insert().values(import_transaction_inserts))
            self._update_metrics(n_insertions=len(import_transaction_inserts))

        if transaction_inserts:
            db.engine.execute(models.Transaction.__table__.insert().values(transaction_inserts))

        if self.feed_type_is_payment:
            # payment imports need to get identified before they can be matched
            for args in identify_args:
                tasks.identify_user_queue.enqueue(tasks.identify_user, feed_type=self.feed_type, **args._asdict())
        elif self.feed_type == FeedType.MERCHANT:
            # merchant imports can go straight to matching/streaming
            tasks.import_queue.enqueue(tasks.import_transactions, match_group)

        return len(new)

    def _build_inserts(
        self, tx_data: dict, match_group: str, source: str, *, session: db.Session
    ) -> tuple[dict, t.Optional[dict], t.Optional[IdentifyArgs]]:
        tid = self.get_transaction_id(tx_data)
        mids = self.get_mids(tx_data)

        merchant_identifier_ids = []
        for mid in mids:
            try:
                merchant_identifier_ids.extend(self._identify_mid(mid, session=session))
            except MissingMID:
                pass

        identified = len(merchant_identifier_ids) > 0

        import_transaction_insert = dict(
            transaction_id=tid,
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
