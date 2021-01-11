import typing as t

from marshmallow import Schema, fields

from app import db, feeds
from app.imports.agents import PassiveAPIAgent, SchemeTransactionFields
from app.serialization import PendulumField


class TransactionSchema(Schema):
    tid = fields.String(required=True, allow_none=False)
    mid = fields.String(required=True, allow_none=False)
    date = PendulumField(required=True, allow_none=False, tz="Europe/London")
    spend = fields.Integer(required=True, allow_none=False)
    payment_provider_slug = fields.String(required=True, allow_none=False)


class BinkLoyalty(PassiveAPIAgent):
    provider_slug = "bink-loyalty"
    feed_type = feeds.ImportFeedTypes.MERCHANT
    schema = TransactionSchema()

    def help(self, session: db.Session) -> str:
        return self._help(__name__)

    def to_transaction_fields(self, data: dict) -> SchemeTransactionFields:
        return SchemeTransactionFields(
            transaction_date=data["date"],
            has_time=True,
            payment_provider_slug=data["payment_provider_slug"],
            spend_amount=data["spend"],
            spend_multiplier=100,
            spend_currency="GBP",
            extra_fields={},
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["tid"]

    def get_mids(self, data: dict) -> t.List[str]:
        return [data["mid"]]
