import json
import inspect
import typing as t

from app import models
from decimal import Decimal
from app.feeds import ImportFeedTypes
from app.imports.agents import FileAgent
from app.config import KEY_PREFIX, ConfigValue


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
    def to_queue_transaction(
        data: dict, merchant_identifier_ids: t.List[int], transaction_id: str
    ) -> models.SchemeTransaction:
        return models.SchemeTransaction(
            merchant_identifier_ids=merchant_identifier_ids,
            transaction_id=transaction_id,
            transaction_date=data["timestamp"],
            spend_amount=int(Decimal(data["amount"]["value"]) * 100),
            spend_multiplier=100,
            spend_currency=data["amount"]["unit"],
            extra_fields={k: data[k] for k in ("card",)},
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["id"]

    @staticmethod
    def get_mids(data: dict) -> t.List[str]:
        return [data["store_id"]]
