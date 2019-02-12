import typing as t
import inspect
import csv
from decimal import Decimal

import pendulum
from marshmallow import Schema, fields

from app import models
from app.config import KEY_PREFIX, ConfigValue
from app.feeds import ImportFeedTypes
from app.imports.agents.bases.directory_watch_agent import DirectoryWatchAgent

from app.utils import PendulumField

PROVIDER_SLUG = "iceland-bonus-card"
WATCH_DIRECTORY_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.watch_directory"

DATETIME_FORMAT = "YYYY-MM-DD HH:mm:ss"


class IcelandAgentTransactionSchema(Schema):
    TransactionCardFirst6 = fields.String(required=True)
    TransactionCardLast4 = fields.String(required=True)
    TransactionCardExpiry = fields.String(required=True)
    TransactionCardSchemeId = fields.Integer(required=True)
    TransactionCardScheme = fields.String(required=True)
    TransactionStore_Id = fields.String(required=True)
    TransactionTimestamp = PendulumField(required=True, date_format=DATETIME_FORMAT)
    TransactionAmountValue = fields.Decimal(required=True)
    TransactionAmountUnit = fields.String(required=True)
    TransactionCashbackValue = fields.Decimal(required=True)
    TransactionCashbackUnit = fields.String(required=True)
    TransactionId = fields.String(required=True)
    TransactionAuthCode = fields.String(required=True)

    @staticmethod
    def to_queue_transaction(
        data: dict, merchant_identifier_id: int, transaction_id: str
    ) -> models.SchemeTransaction:
        return models.PaymentTransaction(
            merchant_identifier_id=merchant_identifier_id,
            transaction_id=transaction_id,
            transaction_date=pendulum.instance(data["TransactionTimestamp"]),
            spend_amount=int(Decimal(data["TransactionAmountValue"]) * 100),
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
    def get_mid(data: dict) -> str:
        return data["TransactionStore_Id"]


class IcelandAgent(DirectoryWatchAgent):
    schema = IcelandAgentTransactionSchema()
    feed_type = ImportFeedTypes.PAYMENT
    provider_slug = PROVIDER_SLUG

    file_field_types = {
        "TransactionCardSchemeId": int,
        "TransactionAmountValue": Decimal,
        "TransactionCashbackValue": Decimal,
    }

    class Config:
        watch_directory = ConfigValue(
            WATCH_DIRECTORY_KEY, default=f"files/imports/{PROVIDER_SLUG}"
        )

    def yield_transactions_data(self, fd: t.IO) -> t.Iterable[dict]:
        reader = csv.DictReader(fd)
        for raw_data in reader:
            if raw_data["TransactionAuthCode"].lower() == "decline":
                continue

            yield {k: self.file_field_types.get(k, str)(v) for k, v in raw_data.items()}

    def help(self) -> str:
        return inspect.cleandoc(
            f"""
        This is the Iceland payment transaction file import agent.

        It is currently set up to monitor {self.Config.watch_directory} for files to import.
        """
        )
