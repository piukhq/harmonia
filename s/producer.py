#! /usr/bin/env python3
import random
from base64 import b64encode
from collections import namedtuple
from uuid import uuid4

import click
import pendulum

from app import models
from app.db import Base, session

MIDConfig = namedtuple("MIDConfig", "mid location postcode")

LOYALTY_SCHEME_SLUG = "aĉetado"
PAYMENT_PROVIDER_SLUG = "kasisto"
MID_CONFIGS = [
    MIDConfig("1234", "60 Argyll Road, Llandegwning", "LL53 1PH"),
    MIDConfig("2345", "87 Sandyhill Rd, Frostenden", "NR34 3LX"),
    MIDConfig("3456", "90 Front St, Hempstead", "NR12 3ZY"),
    MIDConfig("4567", "110 Stroude Road, Sinnahard", "AB33 1PD"),
    MIDConfig("5678", "18 Annfield Rd, Beal", "TD15 8DZ"),
    MIDConfig("6789", "11 Overton Circle, Littlebeck", "YO22 5BS"),
]


def get(model: Base, query: list) -> Base:
    return session.query(model).filter(*query).one()


loyalty_scheme = get(
    models.LoyaltyScheme, query=[models.LoyaltyScheme.slug == LOYALTY_SCHEME_SLUG]
)

payment_provider = get(
    models.PaymentProvider, query=[models.PaymentProvider.slug == PAYMENT_PROVIDER_SLUG]
)

merchant_identifiers = []
for mid_config in MID_CONFIGS:
    merchant_identifier = get(
        models.MerchantIdentifier,
        query=[models.MerchantIdentifier.mid == mid_config.mid],
    )
    merchant_identifiers.append(merchant_identifier)


def produce_transaction() -> dict:
    now = pendulum.now()
    amount = random.randint(1, 100) * 100
    points = random.randint(1, 1000) * 100
    mid = random.choice(merchant_identifiers)
    token = f"token-{b64encode(uuid4().bytes).decode()}"

    return {
        "mid": mid.mid,
        "scheme_transaction_id": str(uuid4()),
        "payment_transaction_id": str(uuid4()),
        "date": now,
        "spend": amount,
        "points": points,
        "token": token,
    }


def format_scheme_transaction(tx: dict) -> str:
    fields = ["mid", "scheme_transaction_id", "date", "spend", "points"]
    return "\x1f".join(str(tx[f]) for f in fields)


def format_payment_transaction(tx: dict) -> str:
    fields = ["mid", "payment_transaction_id", "date", "spend", "token"]
    return "\x1f".join(str(tx[f]) for f in fields)


def format_transaction(feed: str, tx: dict) -> str:
    if feed == "scheme":
        return format_scheme_transaction(tx)
    elif feed == "payment":
        return format_payment_transaction(tx)
    else:
        raise ValueError(f"{feed} is not a valid feed type")


@click.command()
@click.option("-n", "--count", default=1)
@click.option("--scheme-file", type=click.File(mode="w"), required=True)
@click.option("--payment-file", type=click.File(mode="w"), required=True)
def cli(count: int, scheme_file, payment_file) -> None:
    txs = [produce_transaction() for _ in range(count)]

    for feed, fd in zip(["scheme", "payment"], [scheme_file, payment_file]):
        print("\x1e".join(format_transaction(feed, tx) for tx in txs), end="", file=fd)


if __name__ == "__main__":
    cli()
