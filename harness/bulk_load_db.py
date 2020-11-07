import threading

import click

import factory
from harness.factories.app import factories as app_factories
from harness.factories.app.exports import factories as exports_factories
from harness.factories.app.imports import factories as imports_factories
from harness.factories.common import session

# Define some reasonable defaults
LOYALTY_SCHEME_COUNT = 10
PAYMENT_PROVIDER_COUNT = 3
MERCHANT_IDENTIFIER_COUNT = 200
USER_IDENTITY_COUNT = 8
PAYMENT_TRANSACTION_COUNT = 200
SCHEME_TRANSACTION_COUNT = 2000
MATCHED_TRANSACTION_COUNT = 100
IMPORT_TRANSACTION_COUNT = 2000
EXPORT_TRANSACTION_COUNT = 10
PENDING_EXPORT_COUNT = 10
FILE_SEQUENCE_COUNT = 5


def create_primary_records():
    """
    Create records in the 'base' tables i.e the records that are foreign keys in other tables, and which
    need to be in place to be looked up during fake record creation in those 'many' side tables
    """
    # Create 10 random loyalty schemes
    app_factories.LoyaltySchemeFactory.create_batch(LOYALTY_SCHEME_COUNT)
    # Create our payment providers
    app_factories.PaymentProviderFactory.create_batch(
        PAYMENT_PROVIDER_COUNT, slug=factory.Iterator(["visa", "mastercard", "amex"])
    )
    # Create random merchant ids
    app_factories.MerchantIdentifierFactory.create_batch(MERCHANT_IDENTIFIER_COUNT)
    # Create random users
    app_factories.UserIdentityFactory.create_batch(USER_IDENTITY_COUNT)

    session.commit()


class create_scheme_transactions(threading.Thread):
    def __init__(self, scheme_transaction_count: int):
        self.scheme_transaction_count = scheme_transaction_count
        super().__init__()

    def run(self):
        # Create random scheme transactions
        app_factories.SchemeTransactionFactory.create_batch(self.scheme_transaction_count)
        session.commit()


class create_import_transactions(threading.Thread):
    def __init__(self, import_transaction_count: int):
        self.import_transaction_count = import_transaction_count
        super().__init__()

    def run(self):
        # Create random import transactions
        imports_factories.ImportTransactionFactory.create_batch(self.import_transaction_count)
        session.commit()


def bulk_load_db(scheme_transaction_count: int, import_transaction_count: int, skip_primary: bool):
    # Create our primary records
    if not skip_primary:
        create_primary_records()

    # Create payment transactions, linking to our users
    app_factories.PaymentTransactionFactory.create_batch(PAYMENT_TRANSACTION_COUNT)
    session.commit()

    # These two tables can be asynchronously appended to
    threads = []
    create_scheme_transactions_thread = create_scheme_transactions(scheme_transaction_count=scheme_transaction_count)
    create_import_transactions_thread = create_import_transactions(import_transaction_count=import_transaction_count)
    # Start new Threads
    create_scheme_transactions_thread.start()
    create_import_transactions_thread.start()
    # Add threads to thread list
    threads.append(create_scheme_transactions_thread)
    threads.append(create_import_transactions_thread)
    # Wait for all threads to complete
    for t in threads:
        t.join()

    # Create random matched transactions. This table relies on merchant_identifier, scheme_transaction
    # and payment_transaction rows being in place
    app_factories.MatchedTransactionFactory.create_batch(MATCHED_TRANSACTION_COUNT)
    session.commit()
    # Create random export transactions
    exports_factories.ExportTransactionFactory.create_batch(EXPORT_TRANSACTION_COUNT)
    session.commit()
    # Create random pending exports
    exports_factories.PendingExportFactory.create_batch(PENDING_EXPORT_COUNT)
    session.commit()
    # Create random file sequence records
    exports_factories.FileSequenceNumberFactory.create_batch(FILE_SEQUENCE_COUNT)
    session.commit()


@click.command()
@click.option(
    "--scheme-transaction-count", type=click.INT, default=SCHEME_TRANSACTION_COUNT, show_default=True, required=False
)
@click.option(
    "--import-transaction-count", type=click.INT, default=IMPORT_TRANSACTION_COUNT, show_default=True, required=False
)
@click.option(
    "--skip-primary", is_flag=True, help="Skip creation of base table records", show_default=True, default=False
)
def main(scheme_transaction_count: int, import_transaction_count: int, skip_primary: bool):

    bulk_load_db(
        scheme_transaction_count=scheme_transaction_count,
        import_transaction_count=import_transaction_count,
        skip_primary=skip_primary,
    )


if __name__ == "__main__":
    main()
