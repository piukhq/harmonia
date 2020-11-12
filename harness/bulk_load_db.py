from concurrent.futures import ProcessPoolExecutor

import click

from harness.factories.app import factories as app_factories
from harness.factories.app.exports import factories as exports_factories
from harness.factories.app.imports import factories as imports_factories
from harness.factories.common import session

# Define some reasonable defaults
LOYALTY_SCHEME_COUNT = 10
PAYMENT_PROVIDER_COUNT = 4
MERCHANT_IDENTIFIER_COUNT = 200
USER_IDENTITY_COUNT = 8
PAYMENT_TRANSACTION_COUNT = 200
SCHEME_TRANSACTION_COUNT = 2000
MATCHED_TRANSACTION_COUNT = 100
IMPORT_TRANSACTION_COUNT = 2000
EXPORT_TRANSACTION_COUNT = 10
PENDING_EXPORT_COUNT = 10
FILE_SEQUENCE_COUNT = 5
MAX_PROCESSES = 4
BATCHSIZE = 2000


def create_primary_records(loyalty_scheme_count: int):
    """
    Create records in the 'base' tables i.e the records that are foreign keys in other tables, and which
    need to be in place to be looked up during fake record creation in those 'many' side tables
    """
    # Create 10 random loyalty schemes
    app_factories.LoyaltySchemeFactory.create_batch(loyalty_scheme_count)
    # Create our payment providers
    app_factories.PaymentProviderFactory.create_batch(PAYMENT_PROVIDER_COUNT)
    # Create random merchant ids
    app_factories.MerchantIdentifierFactory.create_batch(MERCHANT_IDENTIFIER_COUNT)
    # Create random users
    app_factories.UserIdentityFactory.create_batch(USER_IDENTITY_COUNT)

    session.commit()


def get_batch_chunks(transaction_count, batchsize):
    while transaction_count > 0:
        if transaction_count >= batchsize:
            yield batchsize
        else:
            yield transaction_count
        transaction_count -= batchsize


def create_scheme_transactions(scheme_transaction_count: int, batchsize: int):
    # Create random scheme transactions
    click.secho(
        f"Creating {scheme_transaction_count} scheme transactions", fg="cyan", bold=True,
    )
    # create batches in chunks of batchsize records, then commit
    chunks = get_batch_chunks(scheme_transaction_count, batchsize=batchsize)
    for chunk in chunks:
        click.secho(
            f"Creating chunk of {chunk} scheme transactions", fg="cyan", bold=True,
        )
        app_factories.SchemeTransactionFactory.create_batch(chunk)
        session.commit()


def create_import_transactions(import_transaction_count: int, batchsize: int):
    # Create random import transactions
    click.secho(
        f"Creating {import_transaction_count} import transactions", fg="cyan", bold=True,
    )
    chunks = get_batch_chunks(import_transaction_count, batchsize=batchsize)
    for chunk in chunks:
        click.secho(
            f"Creating chunk of {chunk} import transactions", fg="cyan", bold=True,
        )
        imports_factories.ImportTransactionFactory.create_batch(chunk)
        session.commit()


def do_async_tables(scheme_transaction_count: int, import_transaction_count: int, max_processes: int, batchsize: int):
    """
    These two tables (import_transactions and scheme_transactions) are the big ones and can be asynchronously
    appended to. import_transactions is a standalone table and data can just be pushed into it
    i.e. it has no foreign keys in other tables
    """
    create_import_transactions_executor = ProcessPoolExecutor(max_workers=max_processes)
    import_transactions_max_processes = int(max_processes / 2)  # There are 2 tables to divide the processes between
    import_transactions_per_process = int(import_transaction_count / import_transactions_max_processes)
    # Create the params for the task
    import_transaction_counts = [import_transactions_per_process for x in range(import_transactions_max_processes)]
    import_transaction_batchsizes = [batchsize for x in range(len(import_transaction_counts))]
    create_import_transactions_executor.map(
        create_import_transactions, import_transaction_counts, import_transaction_batchsizes
    )
    # scheme_transactions provides foreign key links for following tables, so we need to wait for it to
    # complete by using a context manager
    with ProcessPoolExecutor(max_workers=max_processes) as create_scheme_transactions_executor:
        scheme_transactions_max_processes = int(max_processes / 2)  # There are 2 tables to divide the processes between
        scheme_transactions_per_process = int(scheme_transaction_count / scheme_transactions_max_processes)
        # Create the params for the task
        scheme_transaction_counts = [scheme_transactions_per_process for x in range(scheme_transactions_max_processes)]
        scheme_transaction_batchsizes = [batchsize for x in range(len(scheme_transaction_counts))]
        create_scheme_transactions_executor.map(
            create_scheme_transactions, scheme_transaction_counts, scheme_transaction_batchsizes
        )


def bulk_load_db(
    scheme_transaction_count: int,
    import_transaction_count: int,
    loyalty_scheme_count: int,
    payment_transaction_count: int,
    transactions_only: bool,
    max_processes: int,
    batchsize: int,
):
    """
    Main loading function
    """
    if not transactions_only:
        # Create our primary records
        create_primary_records(loyalty_scheme_count)

        # Create payment transactions, linking to our users in the primary table
        app_factories.PaymentTransactionFactory.create_batch(payment_transaction_count)
        session.commit()

    # Do the big transaction tables
    do_async_tables(
        scheme_transaction_count=scheme_transaction_count,
        import_transaction_count=import_transaction_count,
        max_processes=max_processes,
        batchsize=batchsize,
    )

    # The remaining tables
    if not transactions_only:
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
    "--scheme-transaction-count",
    type=click.INT,
    default=SCHEME_TRANSACTION_COUNT,
    show_default=True,
    required=False,
    help="Num records for scheme_transaction table",
)
@click.option(
    "--import-transaction-count",
    type=click.INT,
    default=IMPORT_TRANSACTION_COUNT,
    show_default=True,
    required=False,
    help="Num records for import_transaction table",
)
@click.option(
    "--loyalty-scheme-count",
    type=click.INT,
    default=LOYALTY_SCHEME_COUNT,
    show_default=True,
    required=False,
    help="Num records for loyalty_scheme table",
)
@click.option(
    "--payment-transaction-count",
    type=click.INT,
    default=PAYMENT_TRANSACTION_COUNT,
    show_default=True,
    required=False,
    help="Num records for payment_transaction table",
)
@click.option(
    "--transactions-only",
    is_flag=True,
    help="Only append new records to the two big transaction tables",
    show_default=True,
    default=False,
)
@click.option(
    "--max-processes",
    type=click.INT,
    default=MAX_PROCESSES,
    show_default=True,
    required=False,
    help="Total number of processes to spawn",
)
@click.option(
    "--batchsize",
    type=click.INT,
    default=BATCHSIZE,
    show_default=True,
    required=False,
    help="For large tables, num of records to create between commits (recommended: 2000)",
)
def main(
    scheme_transaction_count: int,
    import_transaction_count: int,
    loyalty_scheme_count: int,
    payment_transaction_count: int,
    transactions_only: bool,
    max_processes: int,
    batchsize: int,
):

    bulk_load_db(
        scheme_transaction_count=scheme_transaction_count,
        import_transaction_count=import_transaction_count,
        loyalty_scheme_count=loyalty_scheme_count,
        payment_transaction_count=payment_transaction_count,
        transactions_only=transactions_only,
        max_processes=max_processes,
        batchsize=batchsize,
    )


if __name__ == "__main__":
    main()
