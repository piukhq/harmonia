import json
import inspect
import typing as t

from app.feeds import ImportFeedTypes
from app.imports.agents import FileAgent
from app.imports.agents.bases import base
from app.config import KEY_PREFIX, ConfigValue
from app.currency import to_pennies

PROVIDER_SLUG = "cooperative"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"


class Cooperative(FileAgent):
    feed_type = ImportFeedTypes.MERCHANT
    provider_slug = PROVIDER_SLUG

    class Config:
        path = ConfigValue(PATH_KEY, default=f"{PROVIDER_SLUG}/")

    def yield_transactions_data(self, data: bytes) -> t.Iterable[dict]:
        yield from json.loads(data.decode())["transactions"]

    def help(self) -> str:
        return inspect.cleandoc(
            f"""
            This is the Cooperative scheme transaction file import agent.

            It is currently set up to monitor {self.Config.path} for files to import.
            """
        )

    @staticmethod
    def to_queue_transaction(data: dict) -> base.SchemeTransaction:
        return base.SchemeTransaction(
            transaction_date=data["timestamp"],
            payment_provider_slug="",
            spend_amount=to_pennies(data["amount"]["value"]),
            spend_multiplier=100,
            spend_currency=data["amount"]["unit"],
            points_amount="",
            points_multiplier="",
            extra_fields={k: data[k] for k in ("card",)},
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["id"]

    @staticmethod
    def get_mids(data: dict) -> t.List[str]:
        return [data["store_id"]]
