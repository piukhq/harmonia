from collections import namedtuple
from functools import lru_cache
import typing as t
import click
import csv

from app.core.identify_retry_worker import IdentifyRetryWorker
from app import models, db
from app.api import auth
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
        loyalty_scheme = db.session.query(models.LoyaltyScheme).filter(models.LoyaltyScheme.slug == slug).first()
        if not loyalty_scheme:
            print(f"adding new loyalty scheme for {slug}")
            loyalty_scheme = models.LoyaltyScheme(slug=slug)
            db.session.add(loyalty_scheme)
            db.session.commit()
        return loyalty_scheme

    @lru_cache(maxsize=256)
    def get_payment_provider(slug: str) -> models.PaymentProvider:
        payment_provider = db.session.query(models.PaymentProvider).filter(models.PaymentProvider.slug == slug).first()
        if not payment_provider:
            print(f"adding new payment provider for {slug}")
            payment_provider = models.PaymentProvider(slug=slug)
            db.session.add(payment_provider)
            db.session.commit()
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
    db.engine.execute(models.MerchantIdentifier.__table__.insert().values(insertions))


@cli.command()
def create_administrator():
    while True:
        email_address = click.prompt("Email address")
        if len(email_address) >= 3 and "@" in email_address[1:-1]:
            break
        click.echo("Please enter a valid email address.")

    while True:
        password = click.prompt("Password", hide_input=True)
        password_confirm = click.prompt("Password (again)", hide_input=True)
        if password == password_confirm:
            break
        click.echo("Passwords don't match. Try again.")

    auth.create_user(email_address, password)
    click.echo("Added!")


if __name__ == "__main__":
    cli()
