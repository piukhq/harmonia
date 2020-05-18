import json
from uuid import uuid4

from harness.providers.base import BaseImportDataProvider
from app.currency import to_pounds


class HarveyNichols(BaseImportDataProvider):
    def provide(self, fixture: dict) -> bytes:
        return json.dumps(
            {
                "transactions": [
                    {
                        "alt_id": "",
                        "card": {
                            "first_6": user["first_six"],
                            "last_4": user["last_four"],
                            "expiry": "0",
                            "scheme": "AMEX",
                        },
                        "amount": {"value": to_pounds(transaction["amount"]), "unit": "GBP"},
                        "store_id": "0001017   005682",
                        "timestamp": transaction["date"].isoformat(),
                        "id": str(uuid4()),
                        "auth_code": "00000000",
                    }
                    for user in fixture["users"]
                    for transaction in user["transactions"]
                ]
            }
        ).encode()
