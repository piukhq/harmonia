import typing as t
from uuid import uuid4

from harness.providers.base import BaseImportDataProvider


class BinkLoyalty(BaseImportDataProvider):
    def provide(self, fixture: dict) -> t.List[dict]:
        return [
            {
                "date": transaction["date"].isoformat(),
                "mid": transaction["mid"],
                "spend": transaction["amount"],
                "tid": str(uuid4()),
                "payment_provider_slug": fixture["payment_provider"]["slug"],
            }
            for user in fixture["users"]
            for transaction in user["transactions"]
        ]
