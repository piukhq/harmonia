import typing as t
from uuid import uuid4

from harness.providers.base import BaseImportDataProvider


class BinkPayment(BaseImportDataProvider):
    slug = "bink-payment"

    def provide(self, fixture: dict) -> t.List[dict]:
        transactions = []

        for user in fixture["users"]:
            for transaction in user.get("transactions", []):
                transactions.append(self._build_transaction(transaction, fixture, user["token"]))

        for transaction in fixture["payment_provider"].get("transactions", []):
            transactions.append(self._build_transaction(transaction, fixture, transaction["token"]))
        return transactions

    @staticmethod
    def _build_transaction(transaction: dict, fixture: dict, token: str) -> dict:
        return {
            "date": transaction["date"].isoformat(),
            "mid": fixture["mid"],
            "token": token,
            "spend": transaction["amount"],
            "tid": str(uuid4()),
            "settlement_key": str(uuid4()),
        }
