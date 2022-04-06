import click
import pendulum

import settings
from app import db, models, tasks
from app.exports.retry_worker import ExportRetryWorker
from app.prometheus import prometheus_thread


@click.group()
def cli() -> None:
    if settings.PUSH_PROMETHEUS_METRICS:
        prometheus_thread.start()


@cli.command()
def export_retry() -> None:
    if settings.DEBUG:
        print("Warning: Running in debug mode. Exceptions will not be handled gracefully!")
    worker = ExportRetryWorker()
    worker.run()


@cli.command()
def worker():
    import rq_worker_settings

    tasks.run_worker(rq_worker_settings.QUEUES)


@cli.command()
@click.option("--days", type=int, default=60, help="Number of days to keep data for")
@click.option(
    "--no-user-input", type=bool, is_flag=True, default=False, help="Do not ask for confirmation before purging"
)
def purgedb(days: int = 60, no_user_input: bool = False) -> None:
    DELETE = [
        models.ExportTransaction,
        models.MatchedTransaction,
        models.SchemeTransaction,
        models.PaymentTransaction,
        models.Transaction,
        models.ImportTransaction,
    ]

    date = pendulum.now("utc").subtract(days=days).date()
    click.echo(f"Data from the last {days} days will be preserved.")
    click.secho(f"Purging data from before {date}", fg="red", bold=True)

    if not no_user_input and not click.confirm("Do you want to continue?"):
        raise click.Abort

    def delete(model: db.Base, *, session: db.Session) -> int:
        return session.query(model).where(model.created_at < date).delete(synchronize_session=False)

    with db.session_scope() as session:
        for model in DELETE:
            click.secho(f"Purging {model.__name__}...", fg="cyan")
            deleted = db.run_query(
                lambda: delete(model, session=session),
                session=session,
                description=f"delete {model.__name__} data from before {date}",
            )
            click.secho(f"Deleted {deleted} {model.__name__} records", fg="green")
        session.commit()


if __name__ == "__main__":
    cli()
