import typing as t
from uuid import uuid4

import pendulum

from harness.providers.base import BaseImportDataProvider

PAYMENT_CARD_TYPES = {
    "visa": "VISA",
    "mastercard": "MASTER",
}


class SlimChickens(BaseImportDataProvider):
    def provide(self, fixture: dict) -> t.List[dict]:
        return [
            {
                "transaction_id": str(uuid4()),
                "payment_card_type": PAYMENT_CARD_TYPES[fixture["payment_provider"]["slug"]],
                "payment_card_last_four": user["last_four"],
                "amount": transaction["amount"],
                "currency_code": "GBP",
                "auth_code": transaction["auth_code"],
                "date": pendulum.instance(transaction["date"]).in_tz("Europe/London").format("YYYY-MM-DDTHH:mm:ss"),
                "merchant_identifier": transaction["identifier"],
                "retailer_location_id": "store_1a",
            }
            for user in fixture["users"]
            for transaction in user["transactions"]
        ]
