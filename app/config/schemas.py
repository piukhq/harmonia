from app.api import define_schema
from marshmallow import Schema, fields


@define_schema
class UpdateKeyRequestSchema(Schema):
    value = fields.String(required=True)


@define_schema
class KeyValuePairSchema(Schema):
    key = fields.String(required=True)
    value = fields.String(required=True)
