import typing as t
from uuid import uuid4

from harness.providers.base import BaseImportDataProvider


class Costa(BaseImportDataProvider):
    def provide(self, fixture: dict) -> t.List[dict]:
        return [
            {
                "transaction_id": str(uuid4()),
                "payment_card_type": fixture["payment_provider"]["slug"],
                "payment_card_first_six": user["first_six"],
                "payment_card_last_four": user["last_four"],
                "amount": transaction["amount"] / 100,
                "currency_code": "GBP",
                "auth_code": transaction["auth_code"],
                "date": transaction["date"],
                "merchant_identifier": transaction["identifier"],
                "retailer_location_id": "store_1a",
                "metadata": {},
                "items_ordered": "{"
                '"products":['
                '{"id":"2","productUuid":"534084a0-a6a3-11ec-b020-211a45f43f11"}'
                "]"
                "}",
            }
            for user in fixture["users"]
            for transaction in user["transactions"]
        ]
