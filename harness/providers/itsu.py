import csv
import io
from random import randint

from app.currency import to_pounds
from harness.providers.base import BaseImportDataProvider


class Itsu(BaseImportDataProvider):
    def provide(self, fixture: dict) -> bytes:
        def txid(transaction: dict) -> str:
            location_id = transaction["location_id"].zfill(3)
            digit = location_id[-1].zfill(3)
            sequence_number = randint(10000, 99999)
            return f"{location_id}/{digit}/{sequence_number}"

        transactions = [
            (
                txid(transaction),
                fixture["payment_provider"]["slug"],
                "",  # first six
                user["last_four"],
                to_pounds(transaction["amount"]),
                "GBP",
                transaction["auth_code"],
                transaction["date"].isoformat(),
                "",  # merchant identifier
                transaction["location_id"],
                "",  # transaction data
                "",  # customer id
            )
            for user in fixture["users"]
            for transaction in user["transactions"]
        ]

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            (
                "transaction_id",
                "payment_card_type",
                "payment_card_first_six",
                "payment_card_last_four",
                "amount",
                "currency_code",
                "auth_code",
                "date",
                "merchant_identifier",
                "retailer_location_id",
                "transaction_data",
                "customer_id",
            )
        )
        writer.writerows(transactions)
        return buf.getvalue().encode()
