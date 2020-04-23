import typing as t

from marshmallow import Schema, fields

from app import feeds
from app.imports.agents import PassiveAPIAgent
from app.imports.agents.bases import base
from app.serialization import PendulumField


class TransactionSchema(Schema):
    tid = fields.String(required=True, allow_none=False)
    mid = fields.String(required=True, allow_none=False)
    date = PendulumField(required=True, allow_none=False)
    spend = fields.Integer(required=True, allow_none=False)
    points = fields.Integer(required=True, allow_none=False)
    payment_provider_slug = fields.String(required=True, allow_none=False)


class BinkLoyalty(PassiveAPIAgent):
    provider_slug = "bink-loyalty"
    feed_type = feeds.ImportFeedTypes.MERCHANT
    schema = TransactionSchema()

    def help(self) -> str:
        return self._help(__name__)

    @staticmethod
    def to_queue_transaction(data: dict) -> base.SchemeTransaction:
        return base.SchemeTransaction(
            transaction_date=data["date"],
            payment_provider_slug=data["payment_provider_slug"],
            spend_amount=data["spend"],
            spend_multiplier=100,
            spend_currency="GBP",
            points_amount=data["points"],
            points_multiplier=1,
            extra_fields={},
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["tid"]

    @staticmethod
    def get_mids(data: dict) -> t.List[str]:
        return [data["mid"]]
