#! /usr/bin/env python3
import typing as t
from collections import namedtuple

import sqlalchemy

from app import models
from app.db import Base, session

MIDConfig = namedtuple("MIDConfig", "mid location postcode")

LOYALTY_SCHEME_SLUG = "example-loyalty-scheme"
PAYMENT_PROVIDER_SLUG = "example-payment-provider"
MID_CONFIGS = [
    MIDConfig("1234", "60 Argyll Road, Llandegwning", "LL53 1PH"),
    MIDConfig("2345", "87 Sandyhill Rd, Frostenden", "NR34 3LX"),
    MIDConfig("3456", "90 Front St, Hempstead", "NR12 3ZY"),
    MIDConfig("4567", "110 Stroude Road, Sinnahard", "AB33 1PD"),
    MIDConfig("5678", "18 Annfield Rd, Beal", "TD15 8DZ"),
    MIDConfig("6789", "11 Overton Circle, Littlebeck", "YO22 5BS"),
]


def get_or_create(model: Base, query: list, create_fields: dict) -> t.Tuple[Base, bool]:
    try:
        return session.query(model).filter(*query).one(), False
    except sqlalchemy.orm.exc.NoResultFound:
        obj = model(**create_fields)
        session.add(obj)
        session.commit()
        return obj, True


if __name__ == "__main__":
    loyalty_scheme, created = get_or_create(
        models.LoyaltyScheme,
        query=[models.LoyaltyScheme.slug == LOYALTY_SCHEME_SLUG],
        create_fields={"slug": LOYALTY_SCHEME_SLUG},
    )

    if created:
        print(f"Created loyalty scheme {LOYALTY_SCHEME_SLUG}.")
    else:
        print(f"Loyalty scheme {LOYALTY_SCHEME_SLUG} already exists.")

    payment_provider, created = get_or_create(
        models.PaymentProvider,
        query=[models.PaymentProvider.slug == PAYMENT_PROVIDER_SLUG],
        create_fields={"slug": PAYMENT_PROVIDER_SLUG},
    )

    if created:
        print(f"Created payment provider {PAYMENT_PROVIDER_SLUG}.")
    else:
        print(f"Payment provider {PAYMENT_PROVIDER_SLUG} already exists.")

    for mid_config in MID_CONFIGS:
        merchant_identifier, created = get_or_create(
            models.MerchantIdentifier,
            query=[models.MerchantIdentifier.mid == mid_config.mid],
            create_fields={
                "mid": mid_config.mid,
                "loyalty_scheme_id": loyalty_scheme.id,
                "payment_provider_id": payment_provider.id,
                "location": mid_config.location,
                "postcode": mid_config.postcode,
            },
        )

        if created:
            print(f"Created MID {mid_config.mid}.")
        else:
            print(f"MID {mid_config.mid} already exists.")
