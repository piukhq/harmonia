import typing as t
from functools import lru_cache

import redis.lock

import settings
from app import db, models, tasks
from app.feeds import ImportFeedTypes
from app.imports.exceptions import MissingMID
from app.reporting import get_logger
from app.status import status_monitor
from app.utils import missing_property


@lru_cache(maxsize=2048)
def identify_mid(mid: str, feed_type: ImportFeedTypes, provider_slug: str) -> t.List[int]:
    def find_mid():
        q = db.session.query(models.MerchantIdentifier)

        if feed_type == ImportFeedTypes.SCHEME:
            q = q.join(models.MerchantIdentifier.loyalty_scheme).filter(models.LoyaltyScheme.slug == provider_slug)
        elif feed_type == ImportFeedTypes.PAYMENT:
            q = q.join(models.MerchantIdentifier.payment_provider).filter(models.PaymentProvider.slug == provider_slug)
        else:
            raise ValueError(f"Unsupported feed type: {feed_type}")

        return q.filter(models.MerchantIdentifier.mid == mid).all()

    merchant_identifiers = db.run_query(find_mid, description=f"find {provider_slug} MID")
    return [mid.id for mid in merchant_identifiers]


class BaseAgent:
    class ImportError(Exception):
        pass

    def __init__(self) -> None:
        self.log = get_logger(f"import-agent.{self.provider_slug}")

    @property
    def provider_slug(self) -> str:
        return missing_property(self, "provider_slug")

    @property
    def feed_type(self) -> ImportFeedTypes:
        return missing_property(self, "feed_type")

    def help(self) -> str:
        return (
            "This is a new import agent.\n"
            "Implement all the required methods (see agent base classes) "
            "and override this help method to provide specific information."
        )

    def run(self, *, once: bool = False):
        raise NotImplementedError(
            "Override the run method in your agent to act as the main entry point into the import process."
        )

    @staticmethod
    def to_queue_transaction(
        data: dict, merchant_identifier_ids: t.List[int], transaction_id: str
    ) -> t.Union[models.SchemeTransaction, models.PaymentTransaction]:
        raise NotImplementedError("Override to_queue_transaction in your agent.")

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        raise NotImplementedError("Override get_transaction_id in your agent.")

    @staticmethod
    def get_mids(data: dict) -> t.List[str]:
        raise NotImplementedError("Override get_mids in your agent.")

    def _find_new_transactions(self, provider_transactions: t.List[dict]) -> t.Tuple[t.List[dict], t.List[dict]]:
        """Splits provider_transactions into two lists containing new and duplicate transactions.
        Returns a tuple (new, duplicate)"""

        tids = {self.get_transaction_id(t) for t in provider_transactions}

        # we filter for duplicates in python rather than a SQL "in" clause because it's faster.
        duplicate_ids = {
            row[0]
            for row in db.run_query(
                lambda: db.session.query(models.ImportTransaction.transaction_id)
                .filter(models.ImportTransaction.provider_slug == self.provider_slug)
                .all(),
                description=f"find duplicated {self.provider_slug} import transactions",
            )
            if row[0] in tids
        }

        # Use list of duplicate transaction IDs to partition provider_transactions.
        # seen_tids is used to filter out file duplicates that aren't in the DB yet.
        seen_tids: t.Set[str] = set()
        new: t.List[dict] = []
        duplicate: t.List[dict] = []
        for tx in provider_transactions:
            tid = self.get_transaction_id(tx)
            if tid in duplicate_ids or tid in seen_tids:
                duplicate.append(tx)
            else:
                seen_tids.add(tid)
                new.append(tx)

        self.log.debug(f"Found {len(new)} new and {len(duplicate)} duplicate transactions in import set.")

        return new, duplicate

    def _identify_mid(self, mid: str) -> t.List[int]:
        mids = identify_mid(mid, self.feed_type, self.provider_slug)
        if not mids:
            raise MissingMID
        return mids

    def _import_transactions(self, provider_transactions: t.List[dict], *, source: str) -> None:
        """
        Imports the given list of deserialized provider transactions.
        Creates ImportTransaction instances in the database, and enqueues the
        transaction data to be matched.
        """
        status_monitor.checkin(self)

        new, duplicate = self._find_new_transactions(provider_transactions)

        insertions = []
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
                        merchant_identifier_ids.extend(self._identify_mid(mid))
                    except MissingMID:
                        pass

                identified = len(merchant_identifier_ids) > 0

                if not identified:
                    self.log.debug(f"No MIDs were found for transaction {tid}")

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
                    queue_tx = self.to_queue_transaction(tx_data, merchant_identifier_ids, tid)

                    import_task = {
                        ImportFeedTypes.MERCHANT: tasks.import_scheme_transaction,
                        ImportFeedTypes.AUTH: tasks.import_auth_payment_transaction,
                        ImportFeedTypes.SETTLED: tasks.import_settled_payment_transaction,
                    }[self.feed_type]
                    tasks.import_queue.enqueue(import_task, queue_tx)
            finally:
                lock.release()

        if insertions:
            db.engine.execute(models.ImportTransaction.__table__.insert().values(insertions))
