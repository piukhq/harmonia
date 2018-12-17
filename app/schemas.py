from marshmallow import Schema, fields, post_load

from app import models
from app.db import Session

session = Session()


class SchemeImportQueueSchema(Schema):
    merchant_identifier_id = fields.Integer(required=True, allow_none=False)
    transaction_id = fields.String(required=True, allow_none=False)
    transaction_date = fields.DateTime(required=True, allow_none=False)
    spend_amount = fields.Integer(required=True, allow_none=False)
    spend_multiplier = fields.Integer(required=True, allow_none=False)
    spend_currency = fields.String(required=True, allow_none=False)
    points_amount = fields.Integer(required=True, allow_none=False)
    points_multiplier = fields.Integer(required=True, allow_none=False)
    extra_fields = fields.Dict(required=True, allow_none=False)

    @post_load
    def make_scheme_transaction(self, data: dict) -> models.SchemeTransaction:
        return models.SchemeTransaction(**data)


class PaymentImportQueueSchema(Schema):
    merchant_identifier_id = fields.Integer(required=True, allow_none=False)
    transaction_id = fields.String(required=True, allow_none=False)
    transaction_date = fields.DateTime(required=True, allow_none=False)
    spend_amount = fields.Integer(required=True, allow_none=False)
    spend_multiplier = fields.Integer(required=True, allow_none=False)
    spend_currency = fields.String(required=True, allow_none=False)
    card_token = fields.String(required=True, allow_none=False)
    extra_fields = fields.Dict(required=True, allow_none=False)

    @post_load
    def make_payment_transaction(self, data: dict) -> models.PaymentTransaction:
        return models.PaymentTransaction(**data)


class MatchingQueueSchema(Schema):
    payment_transaction_id = fields.Integer(required=True, allow_none=False)

    @post_load
    def make_payment_transaction_id(self, data: dict) -> int:
        return data["payment_transaction_id"]


class ExportQueueSchema(Schema):
    matched_transaction_id = fields.Integer(required=True, allow_none=False)

    @post_load
    def make_matched_transaction_id(self, data: dict) -> int:
        return data["matched_transaction_id"]


class PendingExportQueueSchema(Schema):
    pending_export_id = fields.Integer(required=True, allow_none=False)

    @post_load
    def make_pending_export_id(self, data: dict) -> int:
        return data["pending_export_id"]
