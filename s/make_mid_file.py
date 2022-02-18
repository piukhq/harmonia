#! /usr/bin/env python3
import csv
from pathlib import Path

import click

from app import db
from app.imports.agents.harvey_nichols import STORE_ID_TO_MIDS
from app.models import LoyaltyScheme, MerchantIdentifier, PaymentProvider


def harvey_nichols_store_id(list_item: list) -> str:
    mid_store = [store for store, mid in STORE_ID_TO_MIDS.items() if list_item[1] in mid]
    return mid_store[0]


@click.group(help="Create a MID csv file from merchant_identifier table in the DB")
def cli() -> None:
    pass


@cli.command(
    help="Create a MID csv file for a loyalty scheme."
    "The file can be used to load MID's into Harmonia for performance testing"
)
@click.argument("loyalty_scheme_slug")
def create_csv(loyalty_scheme_slug: str):
    with db.session_scope() as session:

        def mid_data():
            return (
                session.query(
                    PaymentProvider.slug,
                    MerchantIdentifier.mid,
                    LoyaltyScheme.slug,
                    MerchantIdentifier.store_id,
                    MerchantIdentifier.brand_id,
                    LoyaltyScheme.slug,
                    MerchantIdentifier.location,
                    MerchantIdentifier.postcode,
                )
                .join(LoyaltyScheme)
                .join(PaymentProvider)
                .filter(LoyaltyScheme.slug == loyalty_scheme_slug)
                .distinct()
                .all()
            )

        print("Starting query to read MID data from mid table")
        merchant_identifiers = db.run_query(
            mid_data,
            session=session,
            read_only=True,
            description=f"find {loyalty_scheme_slug} MIDs",
        )
        print(f"Found {len(merchant_identifiers)} mids for {loyalty_scheme_slug}")

        script_dir = Path(__file__).parent.parent
        path = script_dir / "data_generation" / "files" / f"{loyalty_scheme_slug}-mids.csv"
        print(f"Writing mids to csv file in {path}")
        with open(path, "w") as f:
            writer = csv.writer(f)
            for item in merchant_identifiers:
                list_item = list(item)
                if loyalty_scheme_slug == "harvey-nichols":
                    store_id = harvey_nichols_store_id(list_item)
                    list_item[3] = store_id
                list_item[5] = list_item[5].replace("-", " ").title()
                list_item.append("A")
                writer.writerow(list_item)
        print("Finished creating csv file")


if __name__ == "__main__":
    create_csv()
