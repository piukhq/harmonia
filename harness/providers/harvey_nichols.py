import json
from uuid import uuid4

from harness.providers.base import BaseImportDataProvider


class HarveyNichols(BaseImportDataProvider):
    def provide(self, fixture: dict) -> bytes:
        transactions = {
            "transactions": [
                {
                    "alt_id": "",
                    "card": {
                        "first_6": user["first_six"],
                        "last_4": user["last_four"],
                        "expiry": "0",
                        "scheme": "AMEX",
                    },
                    "amount": {"value": transaction["amount"] / 100, "unit": "GBP"},
                    "store_id": "0001017   005682",
                    "timestamp": transaction["date"].isoformat(),
                    "id": str(uuid4()),
                    "auth_code": "00000000",
                }
                for user in fixture["users"]
                for transaction in user["transactions"]
            ]
        }

        return json.dumps(transactions).encode()
