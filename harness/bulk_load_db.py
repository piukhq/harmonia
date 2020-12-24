import time
import typing as t
from concurrent.futures import ProcessPoolExecutor

import click

import factory
from harness.factories.app import factories as app_factories
from harness.factories.app.exports import factories as exports_factories
from harness.factories.app.imports import factories as imports_factories
from harness.factories.common import generic, session

# Define some reasonable defaults
LOYALTY_SCHEME_COUNT = 10
PAYMENT_PROVIDERS = ["visa", "mastercard", "amex"]
MERCHANT_IDENTIFIER_COUNT = 200
USER_IDENTITY_COUNT = 10
PAYMENT_TRANSACTION_COUNT = 200
SCHEME_TRANSACTION_COUNT = 2000
MATCHED_TRANSACTION_COUNT = 100
IMPORT_TRANSACTION_COUNT = 2000
EXPORT_TRANSACTION_COUNT = 10
PENDING_EXPORT_COUNT = 10
FILE_SEQUENCE_COUNT = 5
MAX_PROCESSES = 18
BATCHSIZE = 2000


def create_loyalty_scheme(loyalty_scheme_count: int, scheme_slug: t.Optional[str] = None):
    if scheme_slug:
        # Create the unique loyalty_scheme record for this slug
        app_factories.LoyaltySchemeFactory(slug=scheme_slug)
    else:
        # Create 10 random loyalty schemes
        app_factories.LoyaltySchemeFactory.create_batch(loyalty_scheme_count)


def create_base_records(loyalty_scheme_count: int, scheme_slug: t.Optional[str] = None):
    """
    Create records in the 'base' tables i.e the records that are foreign keys in other tables, and which
    need to be in place to be looked up during fake record creation in those 'many' side tables
    """
    # First thing, as some of the following tables rely on this one: create loyalty_scheme record/s
    create_loyalty_scheme(loyalty_scheme_count, scheme_slug)
    # Create our payment providers
    app_factories.PaymentProviderFactory.create_batch(len(PAYMENT_PROVIDERS), slug=factory.Iterator(PAYMENT_PROVIDERS))
    # Create random merchant ids
    app_factories.MerchantIdentifierFactory.create_batch(MERCHANT_IDENTIFIER_COUNT)
    # Create random users
    app_factories.UserIdentityFactory.create_batch(USER_IDENTITY_COUNT)

    session.commit()


def get_batch_chunks(transaction_count, batchsize):
    while transaction_count > 0:
        if transaction_count >= batchsize:
            yield batchsize
        else:  # The remainder
            yield transaction_count
        transaction_count -= batchsize


def create_payment_transactions(payment_transaction_count: int, batchsize: int, scheme_slug: t.Optional[str] = None):
    # Create random payment transactions
    click.secho(
        f"Creating {payment_transaction_count} payment transactions", fg="cyan", bold=True,
    )
    # create batches in chunks of batchsize records, then commit
    factory_kwargs = {}
    if scheme_slug:  # We need to override some factory attributes if scheme_slug has been passed in
        factory_kwargs = {
            "provider_slug": scheme_slug,
            "transaction_date": factory.LazyAttribute(
                lambda o: generic.transaction_date_provider.transaction_date(days=7)
            ),
        }
    chunks = get_batch_chunks(payment_transaction_count, batchsize=batchsize)
    for chunk in chunks:
        click.secho(
            f"Creating chunk of {chunk} payment transactions", fg="cyan", bold=True,
        )
        app_factories.PaymentTransactionFactory.create_batch(chunk, **factory_kwargs)
        session.commit()


def create_scheme_transactions(scheme_transaction_count: int, batchsize: int, scheme_slug: t.Optional[str] = None):
    # Create random scheme transactions
    click.secho(
        f"Creating {scheme_transaction_count} scheme transactions", fg="cyan", bold=True,
    )
    # create batches in chunks of batchsize records, then commit
    factory_kwargs = {}
    if scheme_slug:  # We need to override some factory attributes if scheme_slug has been passed in
        factory_kwargs = {
            "provider_slug": scheme_slug,
            "transaction_date": factory.LazyAttribute(
                lambda o: generic.transaction_date_provider.transaction_date(days=7)
            ),
        }
    chunks = get_batch_chunks(scheme_transaction_count, batchsize=batchsize)
    for chunk in chunks:
        click.secho(
            f"Creating chunk of {chunk} scheme transactions", fg="cyan", bold=True,
        )
        app_factories.SchemeTransactionFactory.create_batch(chunk, **factory_kwargs)
        session.commit()


def create_import_transactions(import_transaction_count: int, batchsize: int, scheme_slug: t.Optional[str] = None):
    # Create random import transactions
    click.secho(
        f"Creating {import_transaction_count} import transactions", fg="cyan", bold=True,
    )
    factory_kwargs = {}
    if scheme_slug:  # We need to override some factory attributes if scheme_slug has been passed in
        factory_kwargs = {
            "provider_slug": scheme_slug,
        }
    chunks = get_batch_chunks(import_transaction_count, batchsize=batchsize)
    for chunk in chunks:
        click.secho(
            f"Creating chunk of {chunk} import transactions", fg="cyan", bold=True,
        )
        imports_factories.ImportTransactionFactory.create_batch(chunk, **factory_kwargs)
        session.commit()


def do_async_tables(
    scheme_transaction_count: int,
    import_transaction_count: int,
    payment_transaction_count: int,
    max_processes: int,
    batchsize: int,
    scheme_slug: t.Optional[str] = None,
):
    """
    These three tables (import_transactions, payment_transactions and scheme_transactions) are the big ones and
    can be asynchronously appended to.
    """
    #  import_transactions is a standalone table and data can just be pushed into it
    #  i.e. it has no foreign keys in other tables
    import_transactions_max_processes = int(max_processes / 3)  # There are 3 tables to divide the processes between
    create_import_transactions_executor = ProcessPoolExecutor(max_workers=import_transactions_max_processes)
    import_transactions_per_process = int(import_transaction_count / import_transactions_max_processes)
    # Create the params for the task
    import_transaction_counts = [import_transactions_per_process for x in range(import_transactions_max_processes)]
    import_transaction_batchsizes = [batchsize for x in range(len(import_transaction_counts))]
    import_transaction_scheme_slugs = [scheme_slug for x in range(len(import_transaction_counts))]
    # Create task map
    create_import_transactions_executor.map(
        create_import_transactions,
        import_transaction_counts,
        import_transaction_batchsizes,
        import_transaction_scheme_slugs,
    )

    # payment_transactions provides foreign key links for following tables, so we need to wait for it to
    # complete by using a context manager
    payment_transactions_max_processes = int(max_processes / 3)  # There are 3 tables to divide the processes between
    with ProcessPoolExecutor(max_workers=payment_transactions_max_processes) as create_payment_transactions_executor:
        payment_transactions_per_process = int(payment_transaction_count / payment_transactions_max_processes)
        # Create the params for the task
        payment_transaction_counts = [
            payment_transactions_per_process for x in range(payment_transactions_max_processes)
        ]
        payment_transaction_batchsizes = [batchsize for x in range(len(payment_transaction_counts))]
        payment_transaction_scheme_slugs = [scheme_slug for x in range(len(payment_transaction_counts))]
        # Create task map
        create_payment_transactions_executor.map(
            create_payment_transactions,
            payment_transaction_counts,
            payment_transaction_batchsizes,
            payment_transaction_scheme_slugs,
        )

    # scheme_transactions provides foreign key links for following tables, so we need to wait for it to
    # complete by using a context manager
    scheme_transactions_max_processes = int(max_processes / 3)  # There are 3 tables to divide the processes between
    with ProcessPoolExecutor(max_workers=scheme_transactions_max_processes) as create_scheme_transactions_executor:
        scheme_transactions_per_process = int(scheme_transaction_count / scheme_transactions_max_processes)
        # Create the params for the task
        scheme_transaction_counts = [scheme_transactions_per_process for x in range(scheme_transactions_max_processes)]
        scheme_transaction_batchsizes = [batchsize for x in range(len(scheme_transaction_counts))]
        scheme_transaction_scheme_slugs = [scheme_slug for x in range(len(scheme_transaction_counts))]
        # Create task map
        create_scheme_transactions_executor.map(
            create_scheme_transactions,
            scheme_transaction_counts,
            scheme_transaction_batchsizes,
            scheme_transaction_scheme_slugs,
        )


def bulk_load_db(
    scheme_transaction_count: int,
    import_transaction_count: int,
    loyalty_scheme_count: int,
    payment_transaction_count: int,
    skip_base_tables: bool,
    max_processes: int,
    batchsize: int,
    drop_constraints: bool,
    scheme_slug: t.Optional[str] = None,
):
    """
    Main loading function
    """

    # Drop constraints?
    if drop_constraints:
        drop_import_transaction_constraints = "ALTER TABLE import_transaction DISABLE TRIGGER ALL"
        drop_scheme_transaction_constraints = "ALTER TABLE scheme_transaction DISABLE TRIGGER ALL"
        click.secho(
            f"Executing {drop_import_transaction_constraints}", fg="cyan", bold=True,
        )
        session.execute(drop_import_transaction_constraints)
        click.secho(
            f"Executing {drop_scheme_transaction_constraints}", fg="cyan", bold=True,
        )
        session.execute(drop_scheme_transaction_constraints)

    # Skip these base tables if we've already filled them, to avoid constraint errors
    if not skip_base_tables:
        # Create our primary records
        create_base_records(loyalty_scheme_count=loyalty_scheme_count, scheme_slug=scheme_slug)

    # Do the big transaction tables
    do_async_tables(
        scheme_transaction_count=scheme_transaction_count,
        import_transaction_count=import_transaction_count,
        payment_transaction_count=payment_transaction_count,
        max_processes=max_processes,
        batchsize=batchsize,
        scheme_slug=scheme_slug,
    )

    # Do the remaining tables
    # Create random matched transactions. This table relies on merchant_identifier, scheme_transaction
    # and payment_transaction rows being in place
    matched_transaction_factory_kwargs = {}
    if scheme_slug:  # We need to override some factory attributes if scheme_slug has been passed in
        matched_transaction_factory_kwargs = {
            "transaction_date": factory.LazyAttribute(
                lambda o: generic.transaction_date_provider.transaction_date(days=7)
            ),
        }
    app_factories.MatchedTransactionFactory.create_batch(
        MATCHED_TRANSACTION_COUNT, **matched_transaction_factory_kwargs
    )
    session.commit()

    # The remaining factories can use a common factory kwargs
    factory_kwargs = {}
    if scheme_slug:  # We need to override some factory attributes if scheme_slug has been passed in
        factory_kwargs = {
            "provider_slug": scheme_slug,
        }
    # Create random export transactions
    exports_factories.ExportTransactionFactory.create_batch(EXPORT_TRANSACTION_COUNT, **factory_kwargs)
    session.commit()
    # Create random pending exports
    exports_factories.PendingExportFactory.create_batch(PENDING_EXPORT_COUNT, **factory_kwargs)
    session.commit()
    # Create random file sequence records
    exports_factories.FileSequenceNumberFactory.create_batch(FILE_SEQUENCE_COUNT, **factory_kwargs)
    session.commit()

    # Re-enable constraints?
    if drop_constraints:
        enable_import_transaction_constraints = "ALTER TABLE import_transaction ENABLE TRIGGER ALL"
        enable_scheme_transaction_constraints = "ALTER TABLE scheme_transaction ENABLE TRIGGER ALL"
        click.secho(
            f"Executing {enable_import_transaction_constraints}", fg="cyan", bold=True,
        )
        session.execute(enable_import_transaction_constraints)
        click.secho(
            f"Executing {enable_scheme_transaction_constraints}", fg="cyan", bold=True,
        )
        session.execute(enable_scheme_transaction_constraints)


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
    help="Num records for loyalty_scheme table. This will have no effect if --skip-base-tables is used.",
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
    "--skip-base-tables",
    is_flag=True,
    help=(
        "After an initial load, skip the base tables loyalty_scheme, payment_provider, "
        "merchant_identifier and user_identity to avoid constraint errors"
    ),
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
@click.option(
    "--scheme-slug", type=click.STRING, required=False, help="Loyalty scheme slug e.g. harvey-nichols, wasabi-club",
)
@click.option(
    "--drop-constraints",
    is_flag=True,
    help=(
        "Drop constraints on the two big tables with: "
        "ALTER TABLE import_transaction DISABLE TRIGGER ALL; "
        "ALTER TABLE scheme_transaction DISABLE TRIGGER ALL; then re-enable at the end"
    ),
    show_default=True,
    default=False,
)
def main(
    scheme_transaction_count: int,
    import_transaction_count: int,
    loyalty_scheme_count: int,
    payment_transaction_count: int,
    skip_base_tables: bool,
    max_processes: int,
    batchsize: int,
    scheme_slug: str,
    drop_constraints: bool,
):
    """
    Run an initial load of ballast fake data with something like:

    pipenv run python harness/bulk_load_db.py
    --scheme-transaction-count=250000
    --import-transaction-count=250000
    --max-processes=18
    --batchsize=2000
    --loyalty-scheme-count=1000
    --payment-transaction-count=10000
    --drop-constraints

    Then, to add in additional merchant specific schemes something like:

    pipenv run python harness/bulk_load_db.py
    --scheme-transaction-count=250000
    --import-transaction-count=250000
    --max-processes=18
    --batchsize=2000
    --loyalty-scheme-count=1000
    --payment-transaction-count=10000
    --drop-constraints
    --scheme-slug=wasabi-club
    --skip-base-tables

    Please note that after the initial run, when the base tables are filled, you MUST pass in --skip-base-tables to
    avoid constraint errors for those tables

    As it stands, the script can only do one merchant specific run at a time, so you'll need to pass in
    --scheme-slug for each merchant to create their bulk records
    """

    start_time = int(time.time())
    print(f"Start time: {start_time}")

    bulk_load_db(
        scheme_transaction_count=scheme_transaction_count,
        import_transaction_count=import_transaction_count,
        loyalty_scheme_count=loyalty_scheme_count,
        payment_transaction_count=payment_transaction_count,
        skip_base_tables=skip_base_tables,
        max_processes=max_processes,
        batchsize=batchsize,
        drop_constraints=drop_constraints,
        scheme_slug=scheme_slug,
    )

    end_time = int(time.time())
    print(f"End time: {end_time}")
    print(f"Total run time in seconds: {end_time - start_time}")


if __name__ == "__main__":
    main()
