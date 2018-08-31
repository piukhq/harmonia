import inspect
import typing as t

import marshmallow

from app.imports.models import ImportTransaction
from app.db import Session
from app.reporting import get_logger
from app.status import status_monitor
from app import feeds

session = Session()

log = get_logger('agnt')


class ImportTransactionAlreadyExistsError(Exception):
    pass


def _missing_property(obj, prop: str):
    raise NotImplementedError(f"{type(obj).__name__} needs to add a `{prop}` class variable!")


class BaseAgent:
    @property
    def schema_class(self) -> t.Callable:
        return _missing_property(self, 'schema_class')

    @property
    def provider_slug(self) -> str:
        return _missing_property(self, 'provider_slug')

    @property
    def feed(self) -> feeds.Feed:
        return _missing_property(self, 'feed')

    def help(self) -> str:
        return inspect.cleandoc("""
            This is a new import agent.
            Implement all the required methods (see agent base classes) and
            override this help method to provide specific information.
            """)

    def run(self, *, immediate: bool = False, debug: bool = True) -> None:
        raise NotImplementedError(
            inspect.cleandoc("""
            Override the run method in your agent to act as the main entry point
            into the import process.
            """))

    def get_schema(self) -> marshmallow.Schema:
        """
        Returns an instance of the schema class that should be used to load/dump
        transactions for this merchant's transactions data.
        """
        return self.schema_class()

    def _find_new_transactions(self, provider_transactions: t.List[t.Dict]) -> t.Tuple:
        """Splits provider_transactions into two lists containing new and duplicate transactions.
        Returns a tuple (new, duplicate)"""
        schema = self.get_schema()
        tids = [schema.get_transaction_id(t) for t in provider_transactions]
        duplicate_ids = [
            t[0] for t in session.query(ImportTransaction.transaction_id).filter(
                ImportTransaction.transaction_id.in_(tids)).all()
        ]
        new: t.List[t.Dict] = []
        duplicate: t.List[t.Dict] = []
        for tid, tx in zip(tids, provider_transactions):
            (duplicate if tid in duplicate_ids else new).append(tx)
        log.info(f"Found {len(new)} new and {len(duplicate)} duplicate transactions in import set.")
        return new, duplicate

    def _persist_import_transactions(self, provider_transactions: t.List[t.Dict]) -> None:
        """Saves provider_transactions to the import_transactions table."""
        log.info(f"Saving {len(provider_transactions)} provider transaction(s) to import_transactions table.")
        schema = self.get_schema()
        for tx in provider_transactions:
            session.add(
                ImportTransaction(
                    transaction_id=schema.get_transaction_id(tx), provider_slug=self.provider_slug, data=tx))
        session.commit()

    def _translate_provider_transactions(self, provider_transactions: t.List[t.Dict]) -> t.List:
        """Translates provider_transactions to a list of SchemeTransaction or PaymentTransaction instances.
        Returns the list of transaction instances."""
        schema = self.get_schema()
        log.info(f"Translating {len(provider_transactions)} provider transaction(s) to queue schema.")
        return [schema.to_queue_transaction(tx) for tx in provider_transactions]

    def _import_transactions(self, provider_transactions: t.List[t.Dict]) -> None:
        """
        Imports the given list of deserialized provider transactions.
        Creates ImportTransaction instances in the database, and enqueues the
        transaction data to be matched.
        """
        status_monitor.checkin(self)

        new, duplicate = self._find_new_transactions(provider_transactions)

        if new:
            to_queue = self._translate_provider_transactions(new)
            self.feed.queue.push(to_queue, many=True)
            self._persist_import_transactions(new)
        else:
            log.debug('No new transactions found in import set, not pushing anything to the import queue.')
