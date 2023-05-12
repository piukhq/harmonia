from marshmallow import Schema, fields, validate

from app.api.app import define_schema
from app.models import IdentifierType

NotBlank = validate.Length(min=1)


@define_schema
class IdentifierCreationSchema(Schema):
    identifier = fields.String(required=True, validate=NotBlank)
    identifier_type = fields.String(required=True, validate=validate.OneOf(IdentifierType._member_map_.keys()))
    loyalty_plan = fields.String(required=True, validate=validate.Regexp("^[a-z0-9]+(?:-[a-z0-9]+)*$"))
    payment_scheme = fields.String(required=True, validate=validate.Regexp("^[a-z0-9]+(?:-[a-z0-9]+)*$"))
    location_id = fields.String(required=False, allow_none=True, validate=NotBlank)
    merchant_internal_id = fields.String(required=False, allow_none=True, validate=NotBlank)


@define_schema
class IdentifierCreationListSchema(Schema):
    identifiers = fields.Nested(IdentifierCreationSchema, many=True, required=True)


@define_schema
class IdentifierCreationResultSchema(Schema):
    total = fields.Integer()
    onboarded = fields.Integer()


@define_schema
class IdentifierDeletionSchema(Schema):
    identifier = fields.String(required=True, validate=NotBlank)
    payment_scheme = fields.String(required=True, validate=NotBlank)
    identifier_type = fields.String(required=True, validate=validate.OneOf(IdentifierType._member_map_.keys()))


@define_schema
class IdentifierDeletionListSchema(Schema):
    identifiers = fields.Nested(IdentifierDeletionSchema, many=True, required=True)
    locations = fields.List(fields.String(required=True, validate=NotBlank), required=True)


@define_schema
class IdentifierDeletionResultSchema(Schema):
    deleted = fields.Integer()


@define_schema
class IdentifierUpdateSchema(Schema):
    location_id = fields.String(required=False, allow_none=True, validate=NotBlank)
    merchant_internal_id = fields.String(required=False, allow_none=True, validate=NotBlank)
