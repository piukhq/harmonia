#! /usr/bin/env python3
from collections import namedtuple
from base64 import b64encode
from uuid import uuid4
import random

import sqlalchemy
import pendulum
import click

from app import models, queues
from app.db import Session, Base

session = Session()

MIDConfig = namedtuple('MIDConfig', 'mid location postcode')

LOYALTY_SCHEME_SLUG = 'aĉetado'
PAYMENT_PROVIDER_SLUG = 'kasisto'
MID_CONFIGS = [
    MIDConfig('1234', '60 Argyll Road, Llandegwning', 'LL53 1PH'),
    MIDConfig('2345', '87 Sandyhill Rd, Frostenden', 'NR34 3LX'),
    MIDConfig('3456', '90 Front St, Hempstead', 'NR12 3ZY'),
    MIDConfig('4567', '110 Stroude Road, Sinnahard', 'AB33 1PD'),
    MIDConfig('5678', '18 Annfield Rd, Beal', 'TD15 8DZ'),
    MIDConfig('6789', '11 Overton Circle, Littlebeck', 'YO22 5BS'),
]


def get_or_create(model: Base, query: list, create_fields: dict) -> (Base, bool):
    try:
        return session.query(model).filter(*query).one(), False
    except sqlalchemy.orm.exc.NoResultFound:
        print(f"creating a new {model.__name__}…")
        obj = model(**create_fields)
        session.add(obj)
        session.commit()
        return obj, True


loyalty_scheme, _ = get_or_create(
    models.LoyaltyScheme,
    query=[
        models.LoyaltyScheme.slug == LOYALTY_SCHEME_SLUG,
    ],
    create_fields={
        'slug': LOYALTY_SCHEME_SLUG,
    })

payment_provider, _ = get_or_create(
    models.PaymentProvider,
    query=[
        models.PaymentProvider.slug == PAYMENT_PROVIDER_SLUG,
    ],
    create_fields={
        'slug': PAYMENT_PROVIDER_SLUG,
    })

merchant_identifiers = []
for mid_config in MID_CONFIGS:
    merchant_identifier, _ = get_or_create(
        models.MerchantIdentifier,
        query=[
            models.MerchantIdentifier.mid == mid_config.mid,
        ],
        create_fields={
            'mid': mid_config.mid,
            'loyalty_scheme_id': loyalty_scheme.id,
            'payment_provider_id': payment_provider.id,
            'location': mid_config.location,
            'postcode': mid_config.postcode,
        })
    merchant_identifiers.append(merchant_identifier)


def produce_transaction():
    now = pendulum.now()
    amount = random.randint(1, 100) * 100
    points = random.randint(1, 1000) * 100
    mid = random.choice(merchant_identifiers)
    token = b64encode(uuid4().bytes).decode()

    st = models.SchemeTransaction(
        merchant_identifier_id=mid.id,
        transaction_id=str(uuid4()),
        transaction_date=now,
        spend_amount=amount,
        spend_multiplier=100,
        spend_currency='GBP',
        points_amount=points,
        points_multiplier=100,
        extra_fields={})

    pt = models.PaymentTransaction(
        merchant_identifier_id=mid.id,
        transaction_id=str(uuid4()),
        transaction_date=now,
        spend_amount=amount,
        spend_multiplier=100,
        spend_currency='GBP',
        card_token=token,
        extra_fields={})

    queues.scheme_import_queue.push(st)
    queues.payment_import_queue.push(pt)

    print(f"pushed stx & ptx for mid#{mid.id}")


def produce():
    while True:
        produce_transaction()
        input('\x1b[7m\u23ce \x1b[0m to produce again')


@click.command()
@click.option('--once', is_flag=True, help='only produce one transaction')
def cli(once: bool) -> None:
    if once is True:
        produce_transaction()
    else:
        try:
            produce()
        except KeyboardInterrupt:
            print('\nbye')


if __name__ == '__main__':
    cli()
