import typing as t

from marshmallow import Schema, fields

from app import models, feeds
from app.imports.agents import PassiveAPIAgent


class TransactionSchema(Schema):
    tid = fields.String(required=True, allow_none=False)
    mid = fields.String(required=True, allow_none=False)
    date = fields.DateTime(required=True, allow_none=False)
    spend = fields.Integer(required=True, allow_none=False)
    token = fields.String(required=True, allow_none=False)


class BinkPayment(PassiveAPIAgent):
    provider_slug = "bink-payment"
    feed_type = feeds.ImportFeedTypes.PAYMENT
    schema = TransactionSchema()

    def help(self) -> str:
        return self._help(__name__)

    @staticmethod
    def to_queue_transaction(
        data: dict, merchant_identifier_ids: t.List[int], transaction_id: str
    ) -> t.Union[models.SchemeTransaction, models.PaymentTransaction]:
        return models.PaymentTransaction(
            merchant_identifier_ids=merchant_identifier_ids,
            transaction_id=transaction_id,
            transaction_date=data["date"],
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
