import click

import settings
from app import tasks
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


if __name__ == "__main__":
    cli()
