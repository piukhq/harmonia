import threading
from concurrent.futures import ThreadPoolExecutor

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
MAX_WORKERS = 4


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


def create_scheme_transactions(scheme_transaction_count: int):
    # Create random scheme transactions
    click.secho(
        f"Creating {scheme_transaction_count} scheme transactions in thread {threading.current_thread()}",
        fg="cyan",
        bold=True,
    )
    app_factories.SchemeTransactionFactory.create_batch(scheme_transaction_count)
    session.commit()


def create_import_transactions(import_transaction_count: int):
    # Create random import transactions
    click.secho(
        f"Creating {import_transaction_count} import transactions in thread {threading.current_thread()}",
        fg="cyan",
        bold=True,
    )
    imports_factories.ImportTransactionFactory.create_batch(import_transaction_count)
    session.commit()


def bulk_load_db(scheme_transaction_count: int, import_transaction_count: int, skip_primary: bool, max_workers: int):
    # Create our primary records
    if not skip_primary:
        create_primary_records()

    # Create payment transactions, linking to our users
    app_factories.PaymentTransactionFactory.create_batch(PAYMENT_TRANSACTION_COUNT)
    session.commit()

    # These two tables can be asynchronously appended to
    create_import_transactions_executor = ThreadPoolExecutor(max_workers=max_workers)
    max_create_import_transaction_count = int(import_transaction_count / max_workers)
    create_import_transaction_counts = [max_create_import_transaction_count for x in range(max_workers)]
    create_import_transactions_executor.map(create_import_transactions, create_import_transaction_counts)

    with ThreadPoolExecutor(max_workers=max_workers) as create_scheme_transactions_executor:
        # create_scheme_transactions_executor = ThreadPoolExecutor(max_workers=max_workers)
        max_create_scheme_transaction_count = int(scheme_transaction_count / max_workers)
        create_scheme_transaction_counts = [max_create_scheme_transaction_count for x in range(max_workers)]
        create_scheme_transactions_executor.map(create_scheme_transactions, create_scheme_transaction_counts)

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
@click.option("--max-workers", type=click.INT, default=MAX_WORKERS, show_default=True, required=False)
def main(scheme_transaction_count: int, import_transaction_count: int, skip_primary: bool, max_workers: int):

    bulk_load_db(
        scheme_transaction_count=scheme_transaction_count,
        import_transaction_count=import_transaction_count,
        skip_primary=skip_primary,
        max_workers=max_workers,
    )


if __name__ == "__main__":
    main()
