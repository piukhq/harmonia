import typing as t

import pendulum
from marshmallow import Schema, fields

from app import models, queues
from app.config import KEY_PREFIX, ConfigValue
from app.db import Session
from app.feeds import ImportFeedTypes
from app.imports.agents.bases.directory_watch_agent import DirectoryWatchAgent
from app.utils import file_split

PROVIDER_SLUG = "aĉetado"
WATCH_DIRECTORY_KEY = f"{KEY_PREFIX}imports.agents.aĉetado.watch_directory"


session = Session()


class PendulumField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return pendulum.DateTime()
        return value.isoformat()

    def _deserialize(self, value, attr, data, **kwargs):
        return pendulum.parse(value)


class AĉetadoAgentTransactionSchema(Schema):
    mid = fields.String(required=True)
    transaction_id = fields.String(required=True)
    date = PendulumField(required=True)
    spend = fields.Integer(required=True)
    points = fields.Integer(required=True)

    @staticmethod
    def to_queue_transaction(
        data: dict, merchant_identifier_id: int
    ) -> models.SchemeTransaction:
        return models.SchemeTransaction(
            merchant_identifier_id=merchant_identifier_id,
            transaction_id=data["transaction_id"],
            transaction_date=pendulum.instance(data["date"]),
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
    def get_mid(data: dict) -> str:
        return data["mid"]


class AĉetadoAgent(DirectoryWatchAgent):
    schema_class = AĉetadoAgentTransactionSchema
    feed_type = ImportFeedTypes.SCHEME
    provider_slug = PROVIDER_SLUG
    queue = queues.scheme_import_queue

    file_fields = ["mid", "transaction_id", "date", "spend", "points"]
    file_field_types = {"spend": int, "points": int}

    class Config:
        watch_directory = ConfigValue(
            WATCH_DIRECTORY_KEY, default="files/imports/aĉetado"
        )

    def yield_transactions_data(self, fd: t.IO[bytes]) -> t.Iterable[dict]:
        for record in file_split(fd, sep="\x1e"):
            raw_data = dict(zip(self.file_fields, record.split("\x1f")))
            yield {
                "mid": raw_data["mid"],
                "transaction_id": raw_data["transaction_id"],
                "date": raw_data["date"],
                "spend": int(raw_data["spend"]),
                "points": int(raw_data["points"]),
            }
