import typing as t
import inspect
from decimal import Decimal

import pendulum
from marshmallow import Schema, fields

from app import models
from app.config import KEY_PREFIX, ConfigValue
from app.feeds import ImportFeedTypes
from app.imports.agents.bases.directory_watch_agent import DirectoryWatchAgent

from app.utils import PendulumField

PROVIDER_SLUG = "visa"
WATCH_DIRECTORY_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.watch_directory"

DATE_FORMAT = "YYYY-MM-DD"
DATETIME_FORMAT = "YYYY-MM-DD-HH.mm.ss"


class VisaAgentTransactionSchema(Schema):
    detail_identifier = fields.String(required=True)
    partner_id = fields.String(required=True)
    transaction_id = fields.String(required=True)
    purchase_date = PendulumField(required=True, date_format=DATE_FORMAT)
    transaction_amount = fields.String(required=True)
    card_token = fields.String(required=True)
    merchant_number = fields.String(required=True)
    transaction_date = PendulumField(required=True, date_format=DATETIME_FORMAT)
    alias_card_number = fields.String(required=True)

    @staticmethod
    def to_queue_transaction(
        data: dict, merchant_identifier_id: int, transaction_id: str
    ) -> models.PaymentTransaction:
        return models.PaymentTransaction(
            merchant_identifier_id=merchant_identifier_id,
            transaction_id=transaction_id,
            transaction_date=pendulum.instance(data["purchase_date"]),
            spend_amount=int(Decimal(data["transaction_amount"]) * 100),
            spend_multiplier=100,
            spend_currency="GBP",
            card_token=data["card_token"],
            extra_fields={
                "detail_identifier": data["detail_identifier"],
                "partner_id": data["partner_id"],
                "transaction_date": data["transaction_date"],
                "alias_card_number": data["alias_card_number"],
            },
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["transaction_id"]

    @staticmethod
    def get_mid(data: dict) -> str:
        return data["merchant_number"]


class VisaAgent(DirectoryWatchAgent):
    schema = VisaAgentTransactionSchema()
    feed_type = ImportFeedTypes.PAYMENT
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

    file_field_types = {"spend": int}

    class Config:
        watch_directory = ConfigValue(
            WATCH_DIRECTORY_KEY, default=f"files/imports/{PROVIDER_SLUG}"
        )

    def yield_transactions_data(self, fd: t.IO) -> t.Iterable[dict]:
        for line in fd.readlines():
            raw_data = [l.strip() for l in line.split("|")]

            if not raw_data or raw_data[0] != "D":
                continue

            yield {
                k: self.file_field_types.get(k, str)(v)
                for k, v in zip(self.file_fields, raw_data)
            }

    def help(self) -> str:
        return inspect.cleandoc(
            f"""
        This is the Visa payment transaction file import agent.

        It is currently set up to monitor {self.Config.watch_directory} for files to import.
        """
        )
