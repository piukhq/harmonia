import typing as t

import marshmallow
from sqlalchemy.orm.exc import NoResultFound

from app import models, base_agent
from app.db import Session
from app.feeds import ImportFeedTypes
from app.imports.exceptions import MissingMID
from app.queues import StrictQueue
from app.reporting import get_logger
from app.status import status_monitor
from app.utils import missing_property

session = Session()


class ImportTransactionAlreadyExistsError(Exception):
    pass


class BaseAgent(base_agent.BaseAgent):
    def __init__(self, *, debug: bool = False) -> None:
        self.log = get_logger(f"import-agent.{self.provider_slug}")
        self.debug = debug

    @property
    def schema_class(self) -> t.Callable:
        return missing_property(self, "schema_class")

    @property
    def provider_slug(self) -> str:
        return missing_property(self, "provider_slug")

    @property
    def queue(self) -> StrictQueue:
        return missing_property(self, "queue")

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

    def get_schema(self) -> marshmallow.Schema:
        """
        Returns an instance of the schema class that should be used to load/dump
        transactions for this merchant's transactions data.
        """
        return self.schema_class()

    def _find_new_transactions(
        self, provider_transactions: t.List[dict]
    ) -> t.Tuple[t.List[dict], t.List[dict]]:
        """Splits provider_transactions into two lists containing new and duplicate transactions.
        Returns a tuple (new, duplicate)"""
        schema = self.get_schema()
        tids = [schema.get_transaction_id(t) for t in provider_transactions]
        duplicate_ids = {
            t[0]
            for t in session.query(models.ImportTransaction.transaction_id)
            .filter(
                models.ImportTransaction.transaction_id.in_(tids),
                models.ImportTransaction.provider_slug == self.provider_slug,
            )
            .all()
        }
        new: t.List[dict] = []
        duplicate: t.List[dict] = []
        for tid, tx in zip(tids, provider_transactions):
            (duplicate if tid in duplicate_ids else new).append(tx)
        self.log.info(
            f"Found {len(new)} new and {len(duplicate)} duplicate transactions in import set."
        )
        return new, duplicate

    def _identify_transaction(self, mid: str) -> int:
        try:
            q = session.query(models.MerchantIdentifier)

            if self.feed_type == ImportFeedTypes.SCHEME:
                q = q.join(models.MerchantIdentifier.loyalty_scheme).filter(
                    models.LoyaltyScheme.slug == self.provider_slug
                )
            elif self.feed_type == ImportFeedTypes.PAYMENT:
                q = q.join(models.MerchantIdentifier.payment_provider).filter(
                    models.PaymentProvider.slug == self.provider_slug
                )
            else:
                raise ValueError(f"Unsupported feed type: {self.feed_type}")

            q = q.filter(models.MerchantIdentifier.mid == mid)
            merchant_identifier = q.one()
        except NoResultFound as ex:
            raise MissingMID from ex
        return merchant_identifier.id

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
        schema = self.get_schema()

        for tx_data in new:
            mid = schema.get_mid(tx_data)
            tid = schema.get_transaction_id(tx_data)
            try:
                merchant_identifier_id = self._identify_transaction(mid)
            except MissingMID:
                self.log.warning(
                    f"Couldn't find MID {mid} for transaction {tid}. "
                    f"Transaction will not be put on the matching queue."
                )
                session.add(
                    models.ImportTransaction(
                        transaction_id=tid,
                        provider_slug=self.provider_slug,
                        identified=False,
                        data=tx_data,
                        source=source,
                    )
                )
            else:
                queue_tx = schema.to_queue_transaction(tx_data, merchant_identifier_id)
                self.queue.push(queue_tx)
                session.add(
                    models.ImportTransaction(
                        transaction_id=tid,
                        provider_slug=self.provider_slug,
                        identified=True,
                        data=tx_data,
                        source=source,
                    )
                )
            session.commit()
