import click

from app import naming
from app.core.export_director import ExportDirector
from app.core.import_director import PaymentImportDirector, SchemeImportDirector
from app.core.matching_retry_worker import MatchingRetryWorker
from app.core.matching_worker import MatchingWorker


def info(text: str) -> str:
    return click.style(text, fg="cyan")


SPLASH = """
██╗  ██╗ █████╗ ██████╗ ███╗   ███╗ ██████╗ ███╗   ██╗██╗ █████╗
██║  ██║██╔══██╗██╔══██╗████╗ ████║██╔═══██╗████╗  ██║██║██╔══██╗
███████║███████║██████╔╝██╔████╔██║██║   ██║██╔██╗ ██║██║███████║
██╔══██║██╔══██║██╔══██╗██║╚██╔╝██║██║   ██║██║╚██╗██║██║██╔══██║
██║  ██║██║  ██║██║  ██║██║ ╚═╝ ██║╚██████╔╝██║ ╚████║██║██║  ██║
╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝"""


@click.group()
@click.option(
    "--splash/--no-splash",
    default=True,
    help="whether or not to show the harmonia splash",
)
def cli(splash: bool) -> None:
    if splash:
        click.echo(SPLASH)


@cli.command()
@click.argument("feed", type=click.Choice(["scheme", "payment"]))
@click.option("--once", is_flag=True, help="only handle one transaction")
@click.option(
    "--debug", is_flag=True, help="prefer raising exceptions to handling errors"
)
def import_director(feed: str, once: bool, debug: bool) -> None:
    director_class = {"scheme": SchemeImportDirector, "payment": PaymentImportDirector}[
        feed
    ]

    director = director_class()

    try:
        director.enter_loop(once=once, debug=debug)
    except KeyboardInterrupt:
        click.echo("\n\nShutting down.\n")


@cli.command()
@click.option("--debug", is_flag=True, help="run the worker in debug mode")
@click.option("--once", is_flag=True, help="only handle one transaction")
def matching_worker(debug: bool, once: bool) -> None:
    worker = MatchingWorker(naming.new(), debug=debug)

    try:
        worker.enter_loop(once)
    except KeyboardInterrupt:
        click.echo("\n\nShutting down.\n")


@cli.command()
@click.option("--debug", is_flag=True, help="run the worker in debug mode")
def matching_retry_worker(debug: bool) -> None:
    worker = MatchingRetryWorker(naming.new(), debug=debug)

    try:
        worker.enter_loop()
    except KeyboardInterrupt:
        click.echo("\n\nShutting down.\n")


@cli.command()
@click.option("--once", is_flag=True, help="only handle one transaction")
@click.option(
    "--debug", is_flag=True, help="prefer raising exceptions to handling errors"
)
def export_director(once: bool, debug: bool) -> None:
    director = ExportDirector()
    try:
        director.enter_loop(once=once, debug=debug)
    except KeyboardInterrupt:
        click.echo("\n\nShutting down.\n")


if __name__ == "__main__":
    cli()
