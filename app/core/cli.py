import click

from app.core.import_director import SchemeImportDirector, PaymentImportDirector
from app.core.matching_worker import MatchingWorker
from app.naming import gfycat_name


def info(text: str) -> str:
    return click.style(text, fg='cyan')


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.argument('feed', type=click.Choice(['scheme', 'payment']))
def import_director(feed: str) -> None:
    director_class = {
        'scheme': SchemeImportDirector,
        'payment': PaymentImportDirector,
    }[feed]

    director = director_class()

    try:
        director.enter_loop()
    except KeyboardInterrupt:
        click.echo('\n\nShutting down.\n')


@cli.command()
def matching_worker() -> None:
    worker = MatchingWorker(gfycat_name())

    try:
        worker.enter_loop()
    except KeyboardInterrupt:
        click.echo('\n\nShutting down.\n')


if __name__ == '__main__':
    cli()
