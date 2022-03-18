from marshmallow import Schema, fields, validate

from app.api.app import define_schema

NotBlank = validate.Length(min=1)


@define_schema
class NewMIDSchema(Schema):
    mid = fields.String(required=True, validate=NotBlank)
    location_id = fields.String(required=False, validate=NotBlank)
    merchant_internal_id = fields.String(required=False, validate=NotBlank)
    loyalty_plan = fields.String(required=True, validate=NotBlank)


@define_schema
class NewMIDListSchema(Schema):
    mids = fields.Nested(NewMIDSchema, many=True, required=True)
