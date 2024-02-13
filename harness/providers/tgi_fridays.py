import csv
import io
from decimal import Decimal
from uuid import uuid4

from app.currency import to_pounds
from harness.providers.base import BaseImportDataProvider

TWO_PLACES = Decimal(10) ** -2


class TGIFridays(BaseImportDataProvider):
    def provide(self, fixture: dict, transaction_id: str) -> bytes:

        transactions = [
            (
                transaction_id(str(uuid4())),
                fixture["payment_provider"]["slug"],
                user["first_six"],  # first six
                user["last_four"],
                to_pounds(transaction["amount"]),
                Decimal((transaction["amount"] / 100) * 0.1).quantize(TWO_PLACES),
                "GBP",
                transaction["auth_code"],
                transaction["date"].isoformat(),
                transaction["identifier"],  # merchant identifier
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
                "gratuity_amount",
                "currency_code",
                "auth_code",
                "date",
                "merchant_identifier",
                "retailer_location_id",
            )
        )
        writer.writerows(transactions)
        return buf.getvalue().encode()
