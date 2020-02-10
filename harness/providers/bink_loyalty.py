import typing as t
from uuid import uuid4

from harness.providers.base import BaseImportDataProvider


class BinkLoyalty(BaseImportDataProvider):
    def provide(self, fixture: dict) -> t.List[dict]:
        transactions = []

        for user in fixture["users"]:
            for transaction in user["transactions"]:
                transactions.append(
                    {
                        "date": transaction["date"].isoformat(),
                        "mid": fixture["mid"],
                        "points": transaction["points"],
                        "spend": transaction["amount"],
                        "tid": str(uuid4()),
                    }
                )

        return transactions
