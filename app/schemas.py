from marshmallow import Schema, post_load, fields

from app import models


class SchemeTransactionSchema(Schema):
    provider_slug = fields.String(required=True, allow_none=False)
    mid = fields.String(required=True, allow_none=False)
    transaction_id = fields.String(required=True, allow_none=False)
    transaction_date = fields.DateTime(required=True, allow_none=False)
    spend_amount = fields.Integer(required=True, allow_none=False)
    spend_multiplier = fields.Integer(required=True, allow_none=False)
    spend_currency = fields.String(required=True, allow_none=False)
    points_amount = fields.Integer(required=True, allow_none=True)
    points_multiplier = fields.Integer(required=True, allow_none=True)

    extra_fields = fields.Dict(required=True, allow_none=False)

    @post_load
    def make_transaction(self, data):
        return models.SchemeTransaction(**data)
