import typing as t

from marshmallow import Schema, fields

from app import feeds
from app.imports.agents import PassiveAPIAgent, PaymentTransactionFields
from app.serialization import PendulumField


class TransactionSchema(Schema):
    tid = fields.String(required=True, allow_none=False)
    mid = fields.String(required=True, allow_none=False)
    date = PendulumField(required=True, allow_none=False)
    spend = fields.Integer(required=True, allow_none=False)
    token = fields.String(required=True, allow_none=False)
    settlement_key = fields.String(required=True, allow_none=False)


class BinkPayment(PassiveAPIAgent):
    provider_slug = "bink-payment"
    feed_type = feeds.ImportFeedTypes.SETTLED
    schema = TransactionSchema()

    def help(self) -> str:
        return self._help(__name__)

    @staticmethod
    def to_transaction_fields(data: dict) -> PaymentTransactionFields:
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

    @staticmethod
    def get_mids(data: dict) -> t.List[str]:
        return [data["mid"]]
