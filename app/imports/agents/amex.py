import typing as t
import inspect
from decimal import Decimal

import pendulum

from app import models
from app.config import KEY_PREFIX, ConfigValue
from app.feeds import ImportFeedTypes
from app.imports.agents import FileAgent

PROVIDER_SLUG = "amex"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"

DATE_FORMAT = "YYYY-MM-DD"
DATETIME_FORMAT = "YYYY-MM-DD-HH.mm.ss"


class Amex(FileAgent):
    feed_type = ImportFeedTypes.SETTLED
    provider_slug = PROVIDER_SLUG

    file_fields = [
        "detail_identifier",
        "partner_id",
        "transaction_id",
        "purchase_date",
        "transaction_amount",
        "card_token",
        "merchant_number",
        "transaction_date",
        "alias_card_number",
    ]

    field_transforms: t.Dict[str, t.Callable] = {
        "purchase_date": lambda x: pendulum.from_format(x, DATE_FORMAT),
        "transaction_date": lambda x: pendulum.from_format(x, DATETIME_FORMAT),
        "transaction_amount": lambda x: int(Decimal(x) * 100),
    }

    class Config:
        path = ConfigValue(PATH_KEY, default=f"{PROVIDER_SLUG}/")

    def help(self) -> str:
        return inspect.cleandoc(
            f"""
        This is the Amex payment transaction file import agent.

        It is currently set up to monitor {self.Config.path} for files to import.
        """
        )

    def yield_transactions_data(self, data: bytes) -> t.Iterable[dict]:
        for line in data.decode().split("\n"):
            raw_data = [l.strip() for l in line.split("|")]

            if not raw_data or raw_data[0] != "D":
                continue

            yield {k: self.field_transforms.get(k, str)(v) for k, v in zip(self.file_fields, raw_data)}

    @staticmethod
    def to_queue_transaction(
        data: dict, merchant_identifier_ids: t.List[int], transaction_id: str
    ) -> models.PaymentTransaction:
        return models.PaymentTransaction(
            merchant_identifier_ids=merchant_identifier_ids,
            transaction_id=transaction_id,
            transaction_date=data["purchase_date"],
            spend_amount=data["transaction_amount"],
            spend_multiplier=100,
            spend_currency="GBP",
            card_token=data["card_token"],
            extra_fields={
                k: data[k] for k in ("detail_identifier", "partner_id", "transaction_date", "alias_card_number")
            },
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["transaction_id"]

    @staticmethod
    def get_mids(data: dict) -> t.List[str]:
        return [data["merchant_number"]]
