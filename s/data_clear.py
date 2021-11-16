import typing as t

import click
import pendulum

from app import db, models, sequences


def get_scheme_related_tx(
    delete_before_str: str, *, session: db.Session
) -> t.Tuple[t.Set[int], t.Set[int], t.Set[int], t.Set[int], t.Set[int], t.Set[int]]:
    def query() -> t.List[t.Tuple[int]]:
        return (
            session.query(
                models.SchemeTransaction.id,
                models.PaymentTransaction.id,
                models.UserIdentity.id,
                models.MatchedTransaction.id,
                models.PendingExport.id,
                models.ExportTransaction.id,
            )
            .join(
                models.MatchedTransaction,
                models.MatchedTransaction.scheme_transaction_id == models.SchemeTransaction.id,
                isouter=True,
            )
            .join(
                models.PaymentTransaction,
                models.MatchedTransaction.payment_transaction_id == models.PaymentTransaction.id,
                isouter=True,
            )
            .join(
                models.UserIdentity,
                models.PaymentTransaction.transaction_id == models.UserIdentity.transaction_id,
                isouter=True,
            )
            .join(
                models.PendingExport,
                models.PendingExport.matched_transaction_id == models.MatchedTransaction.id,
                isouter=True,
            )
            .join(
                models.ExportTransaction,
                models.ExportTransaction.matched_transaction_id == models.MatchedTransaction.id,
                isouter=True,
            )
            .filter(models.SchemeTransaction.created_at < delete_before_str)
            .yield_per(10000)
        )

    click.echo("Searching for transactions based on the scheme_transaction table...")

    results = db.run_query(
        query,
        session=session,
        read_only=True,
        description=f"find scheme tx and related records from before {delete_before_str}",
    )

    scheme_transaction_ids = set()
    payment_transaction_ids = set()
    user_identity_ids = set()
    matched_transaction_ids = set()
    pending_export_ids = set()
    export_transaction_ids = set()

    for record in results:
        scheme_transaction_ids.add(record[0])
        payment_transaction_ids.add(record[1])
        user_identity_ids.add(record[2])
        matched_transaction_ids.add(record[3])
        pending_export_ids.add(record[4])
        export_transaction_ids.add(record[5])

    scheme_transaction_ids.discard(None)
    payment_transaction_ids.discard(None)
    user_identity_ids.discard(None)
    matched_transaction_ids.discard(None)
    pending_export_ids.discard(None)
    export_transaction_ids.discard(None)

    click.echo("Scheme-based query:")
    click.echo(f"Found {len(scheme_transaction_ids)} scheme transactions to delete.")
    click.echo(f"Found {len(payment_transaction_ids)} payment transactions to delete.")
    click.echo(f"Found {len(user_identity_ids)} user identities to delete.")
    click.echo(f"Found {len(matched_transaction_ids)} matched transactions to delete.")
    click.echo(f"Found {len(pending_export_ids)} pending exports to delete.")
    click.echo(f"Found {len(export_transaction_ids)} export transactions to delete.")

    return (
        scheme_transaction_ids,
        payment_transaction_ids,
        user_identity_ids,
        matched_transaction_ids,
        pending_export_ids,
        export_transaction_ids,
    )


def get_payment_related_tx(
    delete_before_str: str, *, session: db.Session
) -> t.Tuple[t.Set[int], t.Set[int], t.Set[int], t.Set[int], t.Set[int], t.Set[int]]:
    def query() -> t.List[t.Tuple[int]]:
        return (
            session.query(
                models.SchemeTransaction.id,
                models.PaymentTransaction.id,
                models.UserIdentity.id,
                models.MatchedTransaction.id,
                models.PendingExport.id,
                models.ExportTransaction.id,
            )
            .join(
                models.MatchedTransaction,
                models.MatchedTransaction.payment_transaction_id == models.PaymentTransaction.id,
                isouter=True,
            )
            .join(
                models.SchemeTransaction,
                models.MatchedTransaction.scheme_transaction_id == models.SchemeTransaction.id,
                isouter=True,
            )
            .join(
                models.UserIdentity,
                models.PaymentTransaction.transaction_id == models.UserIdentity.transaction_id,
                isouter=True,
            )
            .join(
                models.PendingExport,
                models.PendingExport.matched_transaction_id == models.MatchedTransaction.id,
                isouter=True,
            )
            .join(
                models.ExportTransaction,
                models.ExportTransaction.matched_transaction_id == models.MatchedTransaction.id,
                isouter=True,
            )
            .filter(models.PaymentTransaction.created_at < delete_before_str)
            .yield_per(10000)
        )

    click.echo("Searching for transactions based on the payment_transaction table...")

    results = db.run_query(
        query,
        session=session,
        read_only=True,
        description=f"find payment tx and related records from before {delete_before_str}",
    )

    scheme_transaction_ids = set()
    payment_transaction_ids = set()
    user_identity_ids = set()
    matched_transaction_ids = set()
    pending_export_ids = set()
    export_transaction_ids = set()

    for record in results:
        scheme_transaction_ids.add(record[0])
        payment_transaction_ids.add(record[1])
        user_identity_ids.add(record[2])
        matched_transaction_ids.add(record[3])
        pending_export_ids.add(record[4])
        export_transaction_ids.add(record[5])

    scheme_transaction_ids.discard(None)
    payment_transaction_ids.discard(None)
    user_identity_ids.discard(None)
    matched_transaction_ids.discard(None)
    pending_export_ids.discard(None)
    export_transaction_ids.discard(None)

    click.echo("Payment-based query:")
    click.echo(f"Found {len(scheme_transaction_ids)} scheme transactions to delete.")
    click.echo(f"Found {len(payment_transaction_ids)} payment transactions to delete.")
    click.echo(f"Found {len(user_identity_ids)} user identities to delete.")
    click.echo(f"Found {len(matched_transaction_ids)} matched transactions to delete.")
    click.echo(f"Found {len(pending_export_ids)} pending exports to delete.")
    click.echo(f"Found {len(export_transaction_ids)} export transactions to delete.")

    return (
        scheme_transaction_ids,
        payment_transaction_ids,
        user_identity_ids,
        matched_transaction_ids,
        pending_export_ids,
        export_transaction_ids,
    )


def get_import_tx_ids(delete_before_str: str, *, session: db.Session) -> t.Set[int]:
    def query() -> t.List[t.Tuple[int]]:
        return (
            session.query(models.ImportTransaction.id)
            .filter(models.ImportTransaction.created_at < delete_before_str)
            .yield_per(10000)
        )

    click.echo("Searching for import transactions...")

    results = db.run_query(
        query, session=session, read_only=True, description=f"find import transactions from before {delete_before_str}"
    )

    import_transaction_ids = {r[0] for r in results}

    click.echo(f"Found {len(import_transaction_ids)} import transactions to delete.")

    return import_transaction_ids


def combine_query_ids(delete_before_str: str, *, session: db.Session):
    (
        stx_scheme_transaction_ids,
        stx_payment_transaction_ids,
        stx_user_identity_ids,
        stx_matched_transaction_ids,
        stx_pending_export_ids,
        stx_export_transaction_ids,
    ) = get_scheme_related_tx(delete_before_str, session=session)
    click.echo()

    (
        ptx_scheme_transaction_ids,
        ptx_payment_transaction_ids,
        ptx_user_identity_ids,
        ptx_matched_transaction_ids,
        ptx_pending_export_ids,
        ptx_export_transaction_ids,
    ) = get_payment_related_tx(delete_before_str, session=session)
    click.echo()

    click.echo("Combining results...")
    scheme_transaction_ids = stx_scheme_transaction_ids | ptx_scheme_transaction_ids
    payment_transaction_ids = stx_payment_transaction_ids | ptx_payment_transaction_ids
    user_identity_ids = stx_user_identity_ids | ptx_user_identity_ids
    matched_transaction_ids = stx_matched_transaction_ids | ptx_matched_transaction_ids
    pending_export_ids = stx_pending_export_ids | ptx_pending_export_ids
    export_transaction_ids = stx_export_transaction_ids | ptx_export_transaction_ids
    click.echo()

    return (
        scheme_transaction_ids,
        payment_transaction_ids,
        user_identity_ids,
        matched_transaction_ids,
        pending_export_ids,
        export_transaction_ids,
    )


def process():
    click.secho("WARNING: Transaction data prior to the given date is going to be deleted.", fg="red")

    delete_before_str = click.prompt("Enter the date to base the deletion on (YYYY-MM-DD [hh:mm:ss])")
    delete_before = pendulum.parse(delete_before_str)
    delete_before_str = delete_before.isoformat()

    click.echo(f"All transaction records created before {delete_before} will be deleted.")
    click.secho("Double check this date before accepting.")

    if not click.confirm("Is the provided data correct?", default=False):
        click.secho("Process aborted!", fg="red")
        return

    with db.session_scope() as session:
        (
            scheme_transaction_ids,
            payment_transaction_ids,
            user_identity_ids,
            matched_transaction_ids,
            pending_export_ids,
            export_transaction_ids,
        ) = combine_query_ids(delete_before_str, session=session)

        import_transaction_ids = get_import_tx_ids(delete_before_str, session=session)
        click.echo()

        click.echo("Combined totals:")
        click.echo(f"Found {len(import_transaction_ids)} import transactions to delete.")
        click.echo(f"Found {len(scheme_transaction_ids)} scheme transactions to delete.")
        click.echo(f"Found {len(payment_transaction_ids)} payment transactions to delete.")
        click.echo(f"Found {len(user_identity_ids)} user identities to delete.")
        click.echo(f"Found {len(matched_transaction_ids)} matched transactions to delete.")
        click.echo(f"Found {len(pending_export_ids)} pending exports to delete.")
        click.echo(f"Found {len(export_transaction_ids)} export transactions to delete.")
        click.echo()

        if not click.confirm("Proceed with deletion?", default=False):
            click.secho("Process aborted!", fg="red")
            return

        def delete_ids(model: db.Base, ids: t.List[int]):
            if not ids:
                click.echo(f"No {model.__tablename__} records to delete, skipping.")
                return

            total = 0
            click.echo(f"Deleting {len(ids)} {model.__tablename__} records...")
            for batch in sequences.batch(ids, size=10000):
                db.run_query(
                    lambda: session.query(model).filter(model.id.in_(batch)).delete(synchronize_session=False),
                    session=session,
                    description=f"delete {model.__tablename__} instances by ID",
                )
                total += len(batch)
                pc = int(100 * total / len(ids))
                click.echo(f"\rDeleted {total}/{len(ids)} ({pc}%)", nl=False)
            click.echo("\nCommitting session... ", nl=False)
            session.commit()
            click.echo(f"Done!\n{len(ids)} {model.__tablename__} records deleted.\n")

        click.echo("Deleting records in reverse-dependency order...\n")
        delete_ids(models.ExportTransaction, list(export_transaction_ids))
        delete_ids(models.PendingExport, list(pending_export_ids))
        delete_ids(models.MatchedTransaction, list(matched_transaction_ids))
        delete_ids(models.SchemeTransaction, list(scheme_transaction_ids))
        delete_ids(models.PaymentTransaction, list(payment_transaction_ids))
        delete_ids(models.UserIdentity, list(user_identity_ids))
        delete_ids(models.ImportTransaction, list(import_transaction_ids))
        click.echo()

        click.echo("Committing session for good luck...")
        session.commit()

        click.echo()
        click.echo("Done!")


process()
