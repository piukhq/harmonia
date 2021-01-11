import typing as t

from marshmallow import Schema, fields

from app import db, feeds
from app.imports.agents import PassiveAPIAgent, PaymentTransactionFields
from app.serialization import PendulumField


class TransactionSchema(Schema):
    tid = fields.String(required=True, allow_none=False)
    mid = fields.String(required=True, allow_none=False)
    date = PendulumField(required=True, allow_none=False, tz="Europe/London")
    spend = fields.Integer(required=True, allow_none=False)
    token = fields.String(required=True, allow_none=False)
    settlement_key = fields.String(required=True, allow_none=False)


class BinkPayment(PassiveAPIAgent):
    provider_slug = "bink-payment"
    feed_type = feeds.ImportFeedTypes.SETTLED
    schema = TransactionSchema()

    def help(self, session: db.Session) -> str:
        return self._help(__name__)

    def to_transaction_fields(self, data: dict) -> PaymentTransactionFields:
        return PaymentTransactionFields(
            settlement_key=data["settlement_key"],
            transaction_date=data["date"],
            has_time=True,
            spend_amount=data["spend"],
            spend_multiplier=100,
            spend_currency="GBP",
            card_token=data["token"],
            extra_fields={},
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["tid"]

    def get_mids(self, data: dict) -> t.List[str]:
        return [data["mid"]]
