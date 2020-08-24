from app.api.app import define_schema
from marshmallow import Schema, fields


@define_schema
class ForceMatchRequestSchema(Schema):
    payment_transaction_id = fields.Integer(required=True)
    scheme_transaction_id = fields.Integer(required=True)
