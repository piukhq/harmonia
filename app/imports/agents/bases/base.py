import inspect

from sqlalchemy.exc import IntegrityError

from app.imports import models
from app.db import Session
from app.reporting import get_logger

session = Session()

log = get_logger('agnt')


class ImportTransactionAlreadyExistsError(Exception):
    pass


class BaseAgent:
    def help(self):
        return inspect.cleandoc(
            """
            This is a new import agent.
            Implement all the required methods (see app/import/agent.py) and
            override this help method to provide specific information.
            """)

    def run(self, immediate=False):
        raise NotImplementedError(inspect.cleandoc(
            """
            Override the run method in your agent to act as the main entry point
            into the import process.
            """))

    def _create_import_transaction(self, schema, data):
        log.debug(f"Creating import transaction with {schema} for {data}")
        itx = models.ImportTransaction(
            transaction_id=schema.get_transaction_id(data),
            provider_slug=self.provider_slug,
            data=data)

        session.add(itx)

        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            log.warning(
                'Imported transaction appears to be a duplicate. '
                'Raising an ImportTransactionAlreadyExistsError to signify this.')
            raise ImportTransactionAlreadyExistsError
