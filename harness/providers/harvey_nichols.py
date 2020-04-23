import json
from uuid import uuid4

from harness.providers.base import BaseImportDataProvider
from app.currency import to_pounds


class HarveyNichols(BaseImportDataProvider):
    def provide(self, fixture: dict) -> bytes:
        transactions = {
            "transactions": [
                self._build_transaction(transaction, fixture, user["first_six"], user["last_four"])
                for user in fixture["users"]
                for transaction in user.get("transactions", [])
            ]
        }

        transactions["transactions"].extend(
            [
                self._build_transaction(transaction, fixture, transaction["first_six"], transaction["last_four"])
                for transaction in fixture["loyalty_scheme"].get("transactions", [])
            ]
        )

        return json.dumps(transactions).encode()

    @staticmethod
    def _build_transaction(transaction: dict, fixture: dict, first_six: str, last_four: str) -> dict:
        return {
            "alt_id": "",
            "card": {"first_6": first_six, "last_4": last_four, "expiry": "0", "scheme": "AMEX"},
            "amount": {"value": to_pounds(transaction["amount"]), "unit": "GBP"},
            "store_id": "0001017   005682",
            "timestamp": transaction["date"].isoformat(),
            "id": str(uuid4()),
            "auth_code": "00000000",
        }
