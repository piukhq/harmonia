import typing as t
from functools import cached_property, lru_cache
from collections import defaultdict

import redis.lock
import pendulum

import settings
from app import db, models, tasks
from app.feeds import ImportFeedTypes
from app.imports.exceptions import MissingMID
from app.reporting import get_logger
from app.status import status_monitor
from app.utils import missing_property


class SchemeTransactionFields(t.NamedTuple):
    payment_provider_slug: str
    transaction_date: pendulum.DateTime
    has_time: bool
    spend_amount: int
    spend_multiplier: int
    spend_currency: str
    extra_fields: dict
    auth_code: str = ""


class PaymentTransactionFields(t.NamedTuple):
    transaction_date: pendulum.DateTime
    has_time: bool
    spend_amount: int
    spend_multiplier: int
    spend_currency: str
    card_token: str
    settlement_key: str
    extra_fields: dict
    auth_code: str = ""


class FeedTypeHandler(t.NamedTuple):
    model: db.Base
    import_task: t.Callable[[t.Union[models.SchemeTransaction, models.PaymentTransaction]], None]


FEED_TYPE_HANDLERS = {
    ImportFeedTypes.MERCHANT: FeedTypeHandler(
        model=models.SchemeTransaction, import_task=tasks.import_scheme_transactions
    ),
    ImportFeedTypes.AUTH: FeedTypeHandler(
        model=models.PaymentTransaction, import_task=tasks.import_auth_payment_transactions
    ),
    ImportFeedTypes.SETTLED: FeedTypeHandler(
        model=models.PaymentTransaction, import_task=tasks.import_settled_payment_transactions
    ),
}


@lru_cache(maxsize=2048)
def identify_mid(mid: str, feed_type: ImportFeedTypes, provider_slug: str, *, session: db.Session) -> t.List[int]:
    def find_mid():
        q = session.query(models.MerchantIdentifier)

        if feed_type == ImportFeedTypes.MERCHANT:
            q = q.join(models.MerchantIdentifier.loyalty_scheme).filter(models.LoyaltyScheme.slug == provider_slug)
        elif feed_type in (ImportFeedTypes.SETTLED, ImportFeedTypes.AUTH):
            q = q.join(models.MerchantIdentifier.payment_provider).filter(models.PaymentProvider.slug == provider_slug)
        else:
            raise ValueError(f"Unsupported feed type: {feed_type}")

        return q.filter(models.MerchantIdentifier.mid == mid).all()

    merchant_identifiers = db.run_query(
        find_mid, session=session, read_only=True, description=f"find {provider_slug} MID"
    )
    return [mid.id for mid in merchant_identifiers]


class BaseAgent:
    class ImportError(Exception):
        pass

    def __init__(self) -> None:
        self.log = get_logger(f"import-agent.{self.provider_slug}")

    @property
    def provider_slug(self) -> str:
        return missing_property(type(self), "provider_slug")

    @property
    def feed_type(self) -> ImportFeedTypes:
        return missing_property(type(self), "feed_type")

    def help(self) -> str:
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
                    session.query(models.MerchantIdentifier.store_id, models.MerchantIdentifier.mid)
                    .join(models.LoyaltyScheme)
                    .filter(models.LoyaltyScheme.slug == self.provider_slug)
                    .filter(models.MerchantIdentifier.store_id.isnot(None))
                    .distinct()
                )

            data = db.run_query(
                get_data, session=session, read_only=True, description=f"find {self.provider_slug} MIDs by store ID"
            )

        storeid_mid_map = defaultdict(list)
        for (store_id, mid) in data:
            storeid_mid_map[store_id].append(mid)
        return storeid_mid_map

    def get_mids(self, data: dict) -> t.List[str]:
        raise NotImplementedError("Override get_mids in your agent.")

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
                .yield_per(yield_per)
                .filter(models.ImportTransaction.provider_slug == self.provider_slug),
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
    ) -> t.Iterable[None]:
        """
        Imports the given list of deserialized provider transactions.
        Creates ImportTransaction instances in the database, and enqueues the
        transaction data to be matched.
        """
        status_monitor.checkin(self)

        new = self._find_new_transactions(provider_transactions, session=session)

        handler = FEED_TYPE_HANDLERS[self.feed_type]

        # TODO: it may be worth limiting the batch size if files get any larger than 10k transactions.
        insertions = []
        queue_transactions = []

        for tx_data in new:
            tid = self.get_transaction_id(tx_data)

            # attempt to lock this transaction id.
            lock_key = f"{settings.REDIS_KEY_PREFIX}:import-lock:{self.provider_slug}:{tid}"
            lock: redis.lock.Lock = db.redis.lock(lock_key, timeout=300)
            if not lock.acquire(blocking=False):
                self.log.warning(f"Transaction {lock_key} is already locked. Skipping.")
                continue

            try:
                mids = self.get_mids(tx_data)

                merchant_identifier_ids = []
                for mid in mids:
                    try:
                        merchant_identifier_ids.extend(self._identify_mid(mid, session=session))
                    except MissingMID:
                        pass

                identified = len(merchant_identifier_ids) > 0

                insertions.append(
                    dict(
                        transaction_id=tid,
                        provider_slug=self.provider_slug,
                        identified=identified,
                        data=tx_data,
                        source=source,
                    )
                )

                if identified:
                    queue_transactions.append(
                        self._build_queue_transaction(handler.model, tx_data, merchant_identifier_ids, tid)
                    )

            finally:
                lock.release()

            yield

        if insertions:
            db.engine.execute(models.ImportTransaction.__table__.insert().values(insertions))

        tasks.import_queue.enqueue(handler.import_task, queue_transactions)

    def _build_queue_transaction(
        self, model: db.Base, transaction_data: dict, merchant_identifier_ids: t.List[int], transaction_id: str,
    ) -> db.Base:
        """
        Creates a transaction instance depending on the feed type and enqueues the transaction.
        """
        transaction_fields = self.to_transaction_fields(transaction_data)

        return model(
            provider_slug=self.provider_slug,
            merchant_identifier_ids=merchant_identifier_ids,
            transaction_id=transaction_id,
            **transaction_fields._asdict(),
        )
