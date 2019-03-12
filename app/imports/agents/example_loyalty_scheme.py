import typing as t
import inspect

import pendulum

from app import models
from app.config import KEY_PREFIX, ConfigValue
from app.feeds import ImportFeedTypes
from app.imports.agents.bases.file_agent import FileAgent

PROVIDER_SLUG = "example-loyalty-scheme"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"


class ExampleLoyaltySchemeAgent(FileAgent):
    feed_type = ImportFeedTypes.SCHEME
    provider_slug = PROVIDER_SLUG

    file_fields = ["mid", "transaction_id", "date", "spend", "points"]
    field_transforms: t.Dict[str, t.Callable] = {"date": pendulum.parse, "spend": int, "points": int}

    class Config:
        path = ConfigValue(PATH_KEY, default=f"{PROVIDER_SLUG}/")

    def help(self) -> str:
        return inspect.cleandoc(
            f"""
            This is an example loyalty scheme transaction file import agent.

            It is currently set up to monitor {self.Config.path} for files to import.
            """
        )

    def yield_transactions_data(self, data: bytes) -> t.Iterable[dict]:
        for record in data.split(b"\x1e"):
            raw_data = dict(zip(self.file_fields, record.split(b"\x1f")))
            yield {k: self.field_transforms.get(k, str)(v.decode()) for k, v in raw_data.items()}

    @staticmethod
    def to_queue_transaction(
        data: dict, merchant_identifier_ids: t.List[int], transaction_id: str
    ) -> models.SchemeTransaction:
        return models.SchemeTransaction(
            merchant_identifier_ids=merchant_identifier_ids,
            transaction_id=transaction_id,
            transaction_date=data["date"],
            spend_amount=data["spend"],
            spend_multiplier=100,
            spend_currency="GBP",
            points_amount=data["points"],
            points_multiplier=100,
            extra_fields={},
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["transaction_id"]

    @staticmethod
    def get_mids(data: dict) -> t.List[str]:
        return [data["mid"]]
