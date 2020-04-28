import typing as t
from uuid import uuid4

from app.service.hermes import hermes
from harness.providers.base import BaseImportDataProvider


class BinkLoyalty(BaseImportDataProvider):
    def provide(self, fixture: dict) -> t.List[dict]:
        transactions = []

        for user in fixture["users"]:
            for transaction in user.get("transactions", []):
                transactions.append(self._build_transaction(transaction, fixture))

        for transaction in fixture["loyalty_scheme"].get("transactions", []):
            transactions.append(self._build_transaction(transaction, fixture))

        return transactions

    @staticmethod
    def _build_transaction(transaction: dict, fixture: dict) -> dict:
        return {
            "date": transaction["date"].isoformat(),
            "mid": fixture["mid"],
            "points": transaction["points"],
            "spend": transaction["amount"],
            "tid": str(uuid4()),
            "payment_provider_slug": fixture["payment_provider"]["slug"],
        }
