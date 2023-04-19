import typing as t
from uuid import uuid4

import pendulum

from app.currency import to_pounds
from harness.providers.base import BaseImportDataProvider

# field with a fixed length
WidthField = t.Tuple[t.Any, int]


class Costa(BaseImportDataProvider):
    def provide(self, fixture: dict) -> t.List[dict]:
        return [
            {
                "transaction_id": str(uuid4()),
                "payment_card_type": fixture["payment_provider"]["slug"],
                "payment_card_first_six": user["first_six"],
                "payment_card_last_four": user["last_four"],
                "amount": to_pounds(transaction["amount"]),
                "currency_code": "GBP",
                "auth_code": transaction["auth_code"],
                "date": pendulum.instance(transaction["date"]).in_tz("Europe/London").format("YYYY-MM-DDTHH:mm:ss"),
                "merchant_identifier": transaction["identifier"],
                "retailer_location_id": "store_1a",
                "metadata": {},
                "items_ordered": "{"
                                 "\"products\":["
                                 "{\"id\":\"2\",\"productUuid\":\"534084a0-a6a3-11ec-b020-211a45f43f11\"}"
                                 "]"
                                 "}"
            }
            for user in fixture["users"]
            for transaction in user["transactions"]
        ]
