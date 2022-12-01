import re

from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from app.api.app import define_schema
from app.models import IdentifierType

NotBlank = validate.Length(min=1)


@define_schema
class IdentifierCreationSchema(Schema):
    identifier = fields.String(required=True, validate=NotBlank)
    identifier_type = fields.String(required=True, validate=validate.OneOf(IdentifierType._member_map_.keys()))
    loyalty_plan = fields.String(required=True, validate=NotBlank)
    payment_scheme = fields.String(required=True, validate=NotBlank)
    location_id = fields.String(required=False, validate=NotBlank)
    merchant_internal_id = fields.String(required=False, validate=NotBlank)

    @validates_schema
    def validate_slug(self, data, **kwargs):
        validator = re.compile("^[a-z0-9][-\w]+$")  # noqa 
        loyalty_plan = validator.match(data["loyalty_plan"])
        payment_scheme = validator.match(data["payment_scheme"])
        if not loyalty_plan:
            raise ValidationError(message="Cannot validate loyalty_plan slug: {}".format(data["loyalty_plan"]))
        elif not payment_scheme:
            raise ValidationError(message="Cannot validate payment_scheme slug: {}".format(data["payment_scheme"]))


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
