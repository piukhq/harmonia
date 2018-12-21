import typing as t

import pendulum
from marshmallow import Schema, fields

from app import models
from app.config import KEY_PREFIX, ConfigValue
from app.feeds import ImportFeedTypes
from app.imports.agents.bases.directory_watch_agent import DirectoryWatchAgent
from app.utils import file_split, PendulumField

PROVIDER_SLUG = "kasisto"
WATCH_DIRECTORY_KEY = f"{KEY_PREFIX}imports.agents.kasisto.watch_directory"


class KasistoAgentTransactionSchema(Schema):
    mid = fields.String(required=True)
    transaction_id = fields.String(required=True)
    date = PendulumField(required=True)
    spend = fields.Integer(required=True)
    token = fields.String(required=True)

    @staticmethod
    def to_queue_transaction(
        data: dict, merchant_identifier_id: int
    ) -> models.PaymentTransaction:
        return models.PaymentTransaction(
            merchant_identifier_id=merchant_identifier_id,
            transaction_id=data["transaction_id"],
            transaction_date=pendulum.instance(data["date"]),
            spend_amount=data["spend"],
            spend_multiplier=100,
            spend_currency="GBP",
            card_token=data["token"],
            extra_fields={},
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["transaction_id"]

    @staticmethod
    def get_mid(data: dict) -> str:
        return data["mid"]


class KasistoAgent(DirectoryWatchAgent):
    schema_class = KasistoAgentTransactionSchema
    feed_type = ImportFeedTypes.PAYMENT
    provider_slug = PROVIDER_SLUG

    file_fields = ["mid", "transaction_id", "date", "spend", "token"]
    file_field_types = {"spend": int}

    class Config:
        watch_directory = ConfigValue(
            WATCH_DIRECTORY_KEY, default="files/imports/kasisto"
        )

    def yield_transactions_data(self, fd: t.IO) -> t.Iterable[dict]:
        for record in file_split(fd, sep="\x1e"):
            raw_data = dict(zip(self.file_fields, record.split("\x1f")))
            yield {
                "mid": raw_data["mid"],
                "transaction_id": raw_data["transaction_id"],
                "date": raw_data["date"],
                "spend": int(raw_data["spend"]),
                "token": raw_data["token"],
            }
