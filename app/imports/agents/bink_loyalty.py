import typing as t

from marshmallow import Schema, fields

from app import models, feeds
from app.imports.agents import PassiveAPIAgent


class TransactionSchema(Schema):
    tid = fields.String(required=True, allow_none=False)
    mid = fields.String(required=True, allow_none=False)
    date = fields.DateTime(required=True, allow_none=False)
    spend = fields.Integer(required=True, allow_none=False)
    points = fields.Integer(required=True, allow_none=False)


class BinkLoyalty(PassiveAPIAgent):
    provider_slug = "bink-loyalty"
    feed_type = feeds.ImportFeedTypes.SCHEME
    schema = TransactionSchema()

    def help(self) -> str:
        return self._help(__name__)

    @staticmethod
    def to_queue_transaction(
        data: dict, merchant_identifier_ids: t.List[int], transaction_id: str
    ) -> t.Union[models.SchemeTransaction, models.PaymentTransaction]:
        return models.SchemeTransaction(
            merchant_identifier_ids=merchant_identifier_ids,
            transaction_id=transaction_id,
            transaction_date=data["date"],
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
