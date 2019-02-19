import typing as t
from functools import lru_cache

from sqlalchemy.orm.exc import NoResultFound

from app import models, tasks, db
from app.feeds import ImportFeedTypes
from app.imports.exceptions import MissingMID
from app.reporting import get_logger
from app.status import status_monitor
from app.utils import missing_property


class ImportTransactionAlreadyExistsError(Exception):
    pass


@lru_cache(maxsize=2048)
def identify_mid(mid: str, feed_type: ImportFeedTypes, provider_slug: str):
    try:
        q = db.session.query(models.MerchantIdentifier)

        if feed_type == ImportFeedTypes.SCHEME:
            q = q.join(models.MerchantIdentifier.loyalty_scheme).filter(
                models.LoyaltyScheme.slug == provider_slug
            )
        elif feed_type == ImportFeedTypes.PAYMENT:
            q = q.join(models.MerchantIdentifier.payment_provider).filter(
                models.PaymentProvider.slug == provider_slug
            )
        else:
            raise ValueError(f"Unsupported feed type: {feed_type}")

        q = q.filter(models.MerchantIdentifier.mid == mid)
        merchant_identifier = q.one()
    except NoResultFound:
        # An exception would be preferable, but this way lru_cache works properly.
        return None
    return merchant_identifier.id


class BaseAgent:
    def __init__(self, *, debug: bool = False) -> None:
        self.log = get_logger(f"import-agent.{self.provider_slug}")
        self.debug = debug

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
            "Override the run method in your agent to act as the main entry point"
            "into the import process."
        )

    @staticmethod
    def to_queue_transaction(
        data: dict, merchant_identifier_ids: t.List[int], transaction_id: str
    ) -> t.Union[models.SchemeTransaction, models.PaymentTransaction]:
        raise NotImplementedError

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        raise NotImplementedError

    @staticmethod
    def get_mids(data: dict) -> t.List[str]:
        raise NotImplementedError

    def _find_new_transactions(
        self, provider_transactions: t.List[dict]
    ) -> t.Tuple[t.List[dict], t.List[dict]]:
        """Splits provider_transactions into two lists containing new and duplicate transactions.
        Returns a tuple (new, duplicate)"""

        tids = {self.get_transaction_id(t) for t in provider_transactions}

        # we filter for duplicates in python rather than a SQL "in" clause because it's faster.
        duplicate_ids = {
            row[0]
            for row in db.session.query(
                models.ImportTransaction.transaction_id
            )
            .filter(
                models.ImportTransaction.provider_slug == self.provider_slug
            )
            .all()
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

        self.log.info(
            f"Found {len(new)} new and {len(duplicate)} duplicate transactions in import set."
        )

        return new, duplicate

    def _identify_mid(self, mid: str) -> int:
        result = identify_mid(mid, self.feed_type, self.provider_slug)
        if result is None:
            raise MissingMID
        return result

    def _import_transactions(
        self, provider_transactions: t.List[dict], *, source: str
    ) -> None:
        """
        Imports the given list of deserialized provider transactions.
        Creates ImportTransaction instances in the database, and enqueues the
        transaction data to be matched.
        """
        status_monitor.checkin(self)

        new, duplicate = self._find_new_transactions(provider_transactions)

        insertions = []
        for tx_data in new:
            mids = self.get_mids(tx_data)
            tid = self.get_transaction_id(tx_data)

            merchant_identifier_ids = []
            for mid in mids:
                try:
                    merchant_identifier_ids.append(self._identify_mid(mid))
                except MissingMID:
                    pass

            if merchant_identifier_ids:
                identified = True
            else:
                identified = False

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
                queue_tx = self.to_queue_transaction(
                    tx_data, merchant_identifier_ids, tid
                )

                import_task = {
                    ImportFeedTypes.SCHEME: tasks.import_scheme_transaction,
                    ImportFeedTypes.PAYMENT: tasks.import_payment_transaction,
                }[self.feed_type]
                tasks.import_queue.enqueue(import_task, queue_tx)

        if insertions:
            db.engine.execute(
                models.ImportTransaction.__table__.insert().values(insertions)
            )
