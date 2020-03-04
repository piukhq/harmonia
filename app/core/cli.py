from collections import namedtuple
from functools import lru_cache
from pathlib import Path
import typing as t
import csv

import click

from app.core.identify_retry_worker import IdentifyRetryWorker
from app.core import keyring as kr
from app import models, db
import settings


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
@click.argument("mids_file", type=click.File())
def import_mids(mids_file: t.TextIO) -> None:
    @lru_cache(maxsize=256)
    def get_loyalty_scheme(slug: str) -> models.LoyaltyScheme:
        loyalty_scheme = db.run_query(
            lambda: db.session.query(models.LoyaltyScheme).filter(models.LoyaltyScheme.slug == slug).first(),
            description=f"find {slug} loyalty scheme",
        )
        if not loyalty_scheme:
            print(f"adding new loyalty scheme for {slug}")

            def add_scheme():
                loyalty_scheme = models.LoyaltyScheme(slug=slug)
                db.session.add(loyalty_scheme)
                db.session.commit()

            db.run_query(add_scheme, description=f"create {slug} loyalty scheme")
        return loyalty_scheme

    @lru_cache(maxsize=256)
    def get_payment_provider(slug: str) -> models.PaymentProvider:
        payment_provider = db.run_query(
            lambda: db.session.query(models.PaymentProvider).filter(models.PaymentProvider.slug == slug).first(),
            description=f"find {slug} payment provider",
        )
        if not payment_provider:
            print(f"adding new payment provider for {slug}")

            def add_provider():
                payment_provider = models.PaymentProvider(slug=slug)
                db.session.add(payment_provider)
                db.session.commit()

            db.run_query(add_provider, description=f"create {slug} payment provider")
        return payment_provider

    MerchantIdentifier = namedtuple(
        "MerchantIdentifier",
        ["card_provider", "merchant_id", "scheme_provider", "merchant_name", "created_date", "location", "postcode"],
    )

    items = [MerchantIdentifier._make(item) for item in csv.reader(mids_file)]
    insertions = []
    for i, item in enumerate(items):
        print(f"{i+1}/{len(items)} ({int(100 * (i + 1) / len(items))}%)", end="\r")

        loyalty_scheme = get_loyalty_scheme(item.scheme_provider)
        payment_provider = get_payment_provider(item.card_provider)

        insertions.append(
            dict(
                mid=item.merchant_id,
                loyalty_scheme_id=loyalty_scheme.id,
                payment_provider_id=payment_provider.id,
                location=item.location,
                postcode=item.postcode,
            )
        )
    print("\nCommitting…")
    db.run_query(
        lambda: db.engine.execute(models.MerchantIdentifier.__table__.insert().values(insertions)),
        description="insert MIDs",
    )


@cli.group()
def keyring():
    pass


@keyring.command()
@click.argument("slug")
@click.option(
    "--path",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, writable=True, readable=False),
    default="keyring",
    show_default=True,
)
def read(slug: str, path: str):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)

    fmt_slug = click.style(slug, fg="cyan", bold=True)
    fmt_path = click.style(path.name, fg="cyan", bold=True)
    click.echo(f"Reading {fmt_slug} keyring into {fmt_path}")

    manager = kr.KeyringManager()
    try:
        for name, data in manager.get_keyring(slug):
            ring_file = path / name
            fmt_path = click.style(ring_file.name, fg="cyan", bold=True)
            click.echo(f"Writing {fmt_path}...")
            with ring_file.open("wb") as f:
                f.write(data)
    except kr.KeyringDoesNotExistError as ex:
        fmt_err = click.style(str(ex), fg="red", bold=True)
        click.echo(f"Keyring manager raised an error: {fmt_err}")


@keyring.command()
@click.argument("slug")
@click.option("--path", default="keyring", show_default=True)
def write(slug: str, path: str):
    path = Path(path)

    fmt_slug = click.style(slug, fg="cyan", bold=True)
    fmt_path = click.style(path.name, fg="cyan", bold=True)
    click.echo(f"Writing {fmt_slug} keyring from {fmt_path}")

    manager = kr.KeyringManager()
    ring_files = [(path / ring_type).open("rb") for ring_type in kr.RING_TYPES]

    manager.create_keyring(slug, pubring=ring_files[0], secring=ring_files[1], trustdb=ring_files[2])

    for ring_file in ring_files:
        ring_file.close()


if __name__ == "__main__":
    cli()
