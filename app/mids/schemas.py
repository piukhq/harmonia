from marshmallow import Schema, fields, validate

from app.api.app import define_schema

NotBlank = validate.Length(min=1)


@define_schema
class MIDCreationSchema(Schema):
    mid = fields.String(required=True, validate=NotBlank)
    loyalty_plan = fields.String(required=True, validate=NotBlank)
    payment_scheme = fields.String(required=True, validate=NotBlank)
    location_id = fields.String(required=False, validate=NotBlank)
    merchant_internal_id = fields.String(required=False, validate=NotBlank)


@define_schema
class MIDCreationListSchema(Schema):
    mids = fields.Nested(MIDCreationSchema, many=True, required=True)


@define_schema
class MIDDeletionSchema(Schema):
    mid = fields.String(required=True, validate=NotBlank)
    payment_scheme = fields.String(required=True, validate=NotBlank)


@define_schema
class MIDDeletionListSchema(Schema):
    mids = fields.Nested(MIDDeletionSchema, many=True, required=True)
    locations = fields.List(fields.String(required=True, validate=NotBlank), required=True)
