# pylint: disable=missing-module-docstring,missing-function-docstring,missing-class-docstring

import click

from app.event.consumer import Consumer
from app.event.publisher import Publisher
from settings import BLOB_EVENT_CONTAINER, BLOB_STORAGE_DSN, EVENT_HUB_DSN, EVENT_HUB_NAME


@click.group()
def cli():
    pass


@cli.command()
def publish():
    last_event = ""
    with Publisher(EVENT_HUB_DSN, EVENT_HUB_NAME) as publisher:
        while True:
            event = click.prompt("Enter event to send", type=str, default=last_event)

            if not event and last_event:
                event = last_event

            publisher.send(event)
            click.secho(f"Sent {event}", fg="green")
            last_event = event


@cli.command()
def consume():
    with Consumer(BLOB_STORAGE_DSN, BLOB_EVENT_CONTAINER, EVENT_HUB_DSN, EVENT_HUB_NAME) as consumer:
        consumer.consume()


if __name__ == "__main__":
    cli()
