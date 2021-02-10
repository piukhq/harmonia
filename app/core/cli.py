import click

import settings
from app import tasks
from app.core.identify_retry_worker import IdentifyRetryWorker
from app.exports.retry_worker import ExportRetryWorker


@click.group()
def cli() -> None:
    pass


@cli.command()
def identify_retry() -> None:
    if settings.DEBUG:
        print("Warning: Running in debug mode. Exceptions will not be handled gracefully!")
    worker = IdentifyRetryWorker()
    worker.run()


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


if __name__ == "__main__":
    cli()
