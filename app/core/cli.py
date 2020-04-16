import csv
import typing as t
from collections import namedtuple
from functools import lru_cache

import click
import gnupg

import settings
from app import db, models, tasks
from app.core import key_manager
from app.core.identify_retry_worker import IdentifyRetryWorker


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


@cli.command()
def worker():
    import rq_worker_settings

    tasks.run_worker(rq_worker_settings.QUEUES)


@cli.group()
def keys():
    pass


@keys.command()
@click.argument("slug")
@click.argument("key", type=click.File("wb"))
def read(slug: str, key: t.IO[bytes]):
    """Download the SLUG key from the vault into DIRECTORY"""
    fmt_slug = click.style(slug, fg="cyan", bold=True)
    fmt_path = click.style(key.name, fg="cyan", bold=True)
    click.echo(f"Downloading {fmt_slug} key into {fmt_path}")

    manager = key_manager.KeyManager()
    try:
        key_data = manager.read_key(slug)
    except key_manager.KeyDoesNotExistError as ex:
        fmt_err = click.style(str(ex), fg="red", bold=True)
        click.echo(f"Key manager raised an error: {fmt_err}")

    key.write(key_data)


@keys.command()
@click.argument("slug")
@click.argument("key", type=click.File("rb"))
def write(slug: str, key: t.IO[bytes]):
    """Upload KEY to the vault as SLUG"""
    fmt_slug = click.style(slug, fg="cyan", bold=True)
    fmt_path = click.style(key.name, fg="cyan", bold=True)
    click.echo(f"Uploading {fmt_path} to vault as {fmt_slug}.")

    manager = key_manager.KeyManager()
    manager.write_key(slug, key.read())


@keys.command()
@click.argument("email")
@click.argument("passphrase")
def gen(email: str, passphrase: str):
    """Generate a new keypair for EMAIL and dump the secret key to stdout"""
    gpg = gnupg.GPG(**settings.GPG_ARGS)
    input_data = gpg.gen_key_input(name_email=email, passphrase=passphrase)
    key = gpg.gen_key(input_data)
    priv_key_asc = gpg.export_keys(key.fingerprint, secret=True, passphrase=passphrase)
    click.echo(priv_key_asc)


@keys.command()
def list():
    """List all keys in the keychain"""
    gpg = gnupg.GPG(**settings.GPG_ARGS)
    for key in gpg.list_keys():
        print(f"[{key['keyid']}] {key['uids'][0]}")


if __name__ == "__main__":
    cli()
