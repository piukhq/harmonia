from marshmallow import Schema, post_load, fields

from app import models


class SchemeTransactionSchema(Schema):
    transaction_id = fields.String(required=True)
    pence = fields.Integer(required=True)
    card_id = fields.String(required=True)
    points_earned = fields.Integer(required=True, allow_none=True)
    total_points = fields.Integer(required=True, allow_none=True)

    @post_load
    def make_transaction(self, data):
        return models.SchemeTransaction(**data)
