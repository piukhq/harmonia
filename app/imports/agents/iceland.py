import typing as t
import inspect
import csv
import io
from decimal import Decimal

import pendulum

from app import models
from app.config import KEY_PREFIX, ConfigValue
from app.feeds import ImportFeedTypes
from app.imports.agents import FileAgent

PROVIDER_SLUG = "iceland-bonus-card"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"

DATETIME_FORMAT = "YYYY-MM-DD HH:mm:ss"


class Iceland(FileAgent):
    feed_type = ImportFeedTypes.SCHEME
    provider_slug = PROVIDER_SLUG

    field_transforms: t.Dict[str, t.Callable] = {
        "TransactionCardSchemeId": int,
        "TransactionAmountValue": lambda x: int(Decimal(x) * 100),
        "TransactionCashbackValue": Decimal,
        "TransactionTimestamp": lambda x: pendulum.from_format(x, DATETIME_FORMAT),
    }

    class Config:
        path = ConfigValue(PATH_KEY, default=f"{PROVIDER_SLUG}/")

    def yield_transactions_data(self, data: bytes) -> t.Iterable[dict]:
        fd = io.StringIO(data.decode())
        reader = csv.DictReader(fd)
        for raw_data in reader:
            if raw_data["TransactionAuthCode"].lower() == "decline":
                continue

            yield {k: self.field_transforms.get(k, str)(v) for k, v in raw_data.items()}

    def help(self) -> str:
        return inspect.cleandoc(
            f"""
            This is the Iceland payment transaction file import agent.

            It is currently set up to monitor {self.Config.path} for files to import.
            """
        )

    @staticmethod
    def to_queue_transaction(
        data: dict, merchant_identifier_ids: t.List[int], transaction_id: str
    ) -> models.SchemeTransaction:
<<<<<<< HEAD
=======

>>>>>>> Add Iceland import agent with few changes
        return models.SchemeTransaction(
            merchant_identifier_ids=merchant_identifier_ids,
            transaction_id=transaction_id,
            transaction_date=data["TransactionTimestamp"],
            spend_amount=data["TransactionAmountValue"],
            spend_multiplier=100,
            spend_currency=data["TransactionAmountUnit"],
            extra_fields={
                k: data[k]
                for k in (
                    "TransactionCardFirst6",
                    "TransactionCardLast4",
                    "TransactionCardExpiry",
                    "TransactionCardSchemeId",
                    "TransactionCardScheme",
                    "TransactionCashbackValue",
                    "TransactionCashbackUnit",
                    "TransactionAuthCode",
                )
            },
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["TransactionId"]

    @staticmethod
    def get_mids(data: dict) -> t.List[str]:
        return [data["TransactionStore_Id"]]
