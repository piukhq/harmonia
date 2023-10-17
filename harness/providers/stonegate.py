import typing as t
from uuid import uuid4

from app.currency import to_pounds
from harness.providers.base import BaseImportDataProvider

PAYMENT_CARD_TYPES = {"visa": "VS", "mastercard": "MC", "amex": "AX"}


class Stonegate(BaseImportDataProvider):
    def provide(self, fixture: dict) -> t.List[dict]:
        return [
            {
                "transaction_id": str(uuid4()),
                "payment_card_type": PAYMENT_CARD_TYPES[fixture["payment_provider"]["slug"]],
                "payment_card_last_four": user["last_four"],
                "amount": to_pounds(transaction["amount"]),
                "currency_code": "GBP",
                "auth_code": transaction["auth_code"],
                "date": transaction["date"],
                "retailer_location_id": transaction["location_id"],
                "metadata": {
                    "AccountID": str(uuid4()),
                },
            }
            for user in fixture["users"]
            for transaction in user["transactions"]
        ]
