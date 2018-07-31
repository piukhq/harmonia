import inspect
import typing as t

from sqlalchemy.exc import IntegrityError
import marshmallow

from app.imports import models
from app.db import Session
from app.reporting import get_logger
from app.queues import import_queue

session = Session()

log = get_logger('agnt')


class ImportTransactionAlreadyExistsError(Exception):
    pass


def _no_schema_class(obj):
    raise ValueError(f"{obj.__class__.__name__} needs to add a `schema_class` class variable!")


class BaseAgent:
    schema_class = _no_schema_class
    provider_slug = 'PROVIDER_NOT_SET'

    def help(self) -> str:
        return inspect.cleandoc(
            """
            This is a new import agent.
            Implement all the required methods (see agent base classes) and
            override this help method to provide specific information.
            """)

    def run(self, *, immediate: bool = False, debug: bool = True) -> None:
        raise NotImplementedError(inspect.cleandoc(
            """
            Override the run method in your agent to act as the main entry point
            into the import process.
            """))

    def get_schema(self) -> marshmallow.Schema:
        """
        Returns an instance of the schema class that should be used to load/dump
        scheme transactions for this merchant's transactions data.
        """
        return self.schema_class()

    def _create_import_transaction(self, data: t.Dict[str, t.Any]):
        """
        Creates an ImportTransaction in the database for the given data.
        Raises an ImportTransactionAlreadyExistsError if the transaction is not
        unique.
        """
        schema = self.get_schema()
        log.debug(f"Creating import transaction with {schema} for {data}")
        import_transaction = models.ImportTransaction(
            transaction_id=schema.get_transaction_id(data),
            provider_slug=self.provider_slug,
            data=data)

        session.add(import_transaction)

        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            log.warning(
                'Imported transaction appears to be a duplicate. '
                'Raising an ImportTransactionAlreadyExistsError to signify this.')
            raise ImportTransactionAlreadyExistsError

    def _import_transactions(self, transactions_data: t.List[t.Dict[str, t.Any]]) -> None:
        """
        Imports the given list of transaction data elements using the agent's
        schema.
        Creates ImportTransaction instances in the database, and enqueues the
        transaction data to be matched.
        """
        name = self.__class__.__name__
        schema = self.get_schema()
        transactions, errors = schema.load(transactions_data, many=True)

        if errors:
            log.error(f"Import translation for {name} failed: {errors}")
            return
        elif transactions is None:
            log.error(
                f"Import translation for {name} failed: schema.load returned None. Confirm that the schema_class for "
                f"{name} is correct.")
            return
        else:
            log.info(f"Import translation successful for {name}: {len(transactions)} transactions loaded.")

        transactions_to_enqueue = []
        for transaction in transactions:
            try:
                self._create_import_transaction(transaction)
            except ImportTransactionAlreadyExistsError:
                log.info('Not pushing transaction to the import queue as it appears to already exist.')
            else:
                transactions_to_enqueue.append(transaction)

        scheme_transactions = [schema.to_scheme_transaction(tx) for tx in transactions_to_enqueue]
        import_queue.push(scheme_transactions, many=True)
        log.info(f"{len(scheme_transactions)} transactions pushed to import queue.")
