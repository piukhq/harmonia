from marshmallow import Schema, fields

from app.api.app import define_schema


@define_schema
class ForceMatchRequestSchema(Schema):
    payment_transaction_id = fields.Integer(required=True)
    scheme_transaction_id = fields.Integer(required=True)
