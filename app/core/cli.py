import click

from app.core.identify_retry_worker import IdentifyRetryWorker


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.option("-d", "--debug", is_flag=True)
def identify_retry(debug: bool) -> None:
    if debug:
        print(
            "Warning: Running in debug mode. Exceptions will not be handled gracefully!"
        )
    worker = IdentifyRetryWorker(raise_exceptions=debug)
    worker.run()


if __name__ == "__main__":
    cli()
