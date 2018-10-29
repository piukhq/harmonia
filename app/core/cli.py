import click

from app.core.import_director import SchemeImportDirector, PaymentImportDirector
from app.core.matching_worker import MatchingWorker
from app.core.matching_retry_worker import MatchingRetryWorker
from app import naming


def info(text: str) -> str:
    return click.style(text, fg='cyan')


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.argument('feed', type=click.Choice(['scheme', 'payment']))
@click.option('--once', is_flag=True, help='only import one transaction')
def import_director(feed: str, once: bool) -> None:
    director_class = {
        'scheme': SchemeImportDirector,
        'payment': PaymentImportDirector,
    }[feed]

    director = director_class()

    try:
        director.enter_loop(once=once)
    except KeyboardInterrupt:
        click.echo('\n\nShutting down.\n')


@cli.command()
@click.option('--debug', is_flag=True, help='run the worker in debug mode')
def matching_worker(debug: bool) -> None:
    worker = MatchingWorker(naming.new(), debug=debug)

    try:
        worker.enter_loop()
    except KeyboardInterrupt:
        click.echo('\n\nShutting down.\n')


@cli.command()
@click.option('--debug', is_flag=True, help='run the worker in debug mode')
def matching_retry_worker(debug: bool) -> None:
    worker = MatchingRetryWorker(naming.new(), debug=debug)

    try:
        worker.enter_loop()
    except KeyboardInterrupt:
        click.echo('\n\nShutting down.\n')


if __name__ == '__main__':
    cli()
