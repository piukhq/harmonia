import json
import typing as t

import pendulum

from app.config import KEY_PREFIX, Config, ConfigValue
from app.currency import to_pennies
from app.feeds import FeedType
from app.imports.agents.bases.base import SchemeTransactionFields
from app.imports.agents.bases.file_agent import FileAgent

PROVIDER_SLUG = "cooperative"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"
SCHEDULE_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.schedule"


class Cooperative(FileAgent):
    feed_type = FeedType.MERCHANT
    provider_slug = PROVIDER_SLUG
    config = Config(
        ConfigValue("path", key=PATH_KEY, default=f"{PROVIDER_SLUG}/"),
        ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *"),
    )

    def yield_transactions_data(self, data: bytes) -> t.Iterable[dict]:
        yield from json.loads(data.decode())["transactions"]

    def to_transaction_fields(self, data: dict) -> SchemeTransactionFields:
        return SchemeTransactionFields(
            merchant_slug=self.provider_slug,
            payment_provider_slug="",
            transaction_date=self.get_transaction_date(data),
            has_time=True,
            spend_amount=to_pennies(data["amount"]["value"]),
            spend_multiplier=100,
            spend_currency=data["amount"]["unit"],
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["id"]

    def get_primary_identifier(self, data: dict) -> str:
        return data["store_id"]

    def get_mids(self, data: dict) -> t.List[str]:
        return [data["store_id"]]

    def get_transaction_date(self, data: dict) -> pendulum.DateTime:
        return self.pendulum_parse(data["timestamp"], tz="GMT")
