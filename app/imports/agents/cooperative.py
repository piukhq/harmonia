import inspect
import json
import typing as t

import pendulum

from app import db
from app.config import KEY_PREFIX, Config, ConfigValue
from app.currency import to_pennies
from app.feeds import ImportFeedTypes
from app.imports.agents.bases.base import SchemeTransactionFields
from app.imports.agents.bases.file_agent import FileAgent

PROVIDER_SLUG = "cooperative"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"
SCHEDULE_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.schedule"


class Cooperative(FileAgent):
    feed_type = ImportFeedTypes.MERCHANT
    provider_slug = PROVIDER_SLUG
    config = Config(
        ConfigValue("path", key=PATH_KEY, default=f"{PROVIDER_SLUG}/"),
        ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *"),
    )

    def yield_transactions_data(self, data: bytes) -> t.Iterable[dict]:
        yield from json.loads(data.decode())["transactions"]

    def help(self, session: db.Session) -> str:
        return inspect.cleandoc(
            f"""
            This is the Cooperative scheme transaction file import agent.

            It is currently set up to monitor {self.config.get('path', session=session)} for files to import.
            """
        )

    def to_transaction_fields(self, data: dict) -> SchemeTransactionFields:
        return SchemeTransactionFields(
            transaction_date=self.get_transaction_date(data),
            has_time=True,
            payment_provider_slug="",
            spend_amount=to_pennies(data["amount"]["value"]),
            spend_multiplier=100,
            spend_currency=data["amount"]["unit"],
            extra_fields={k: data[k] for k in ("card",)},
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["id"]

    def get_mids(self, data: dict) -> t.List[str]:
        return [data["store_id"]]

    def get_transaction_date(self, data: dict) -> pendulum.DateTime:
        return self.pendulum_parse(data["timestamp"], tz="GMT")
