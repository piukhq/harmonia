from marshmallow import Schema, fields

from app.api.app import define_schema


@define_schema
class UpdateKeyRequestSchema(Schema):
    value = fields.String(required=True)


@define_schema
class KeyValuePairSchema(Schema):
    key = fields.String(required=True)
    value = fields.String(required=True)


@define_schema
class ConfigKeysListSchema(Schema):
    keys = fields.Nested(KeyValuePairSchema, many=True)
