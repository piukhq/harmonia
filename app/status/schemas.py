from app.api import define_schema
from marshmallow import Schema, fields


@define_schema
class CheckinSchema(Schema):
    datetime = fields.DateTime(required=True, allow_none=False)
    human_readable = fields.String(required=True, allow_none=False)
    key = fields.String(required=True, allow_none=False)
    name = fields.String(required=True, allow_none=False)
    seconds_ago = fields.Float(required=True, allow_none=False)
    timestamp = fields.Float(required=True, allow_none=False)


@define_schema
class ServiceHealthSchema(Schema):
    name = fields.String(required=True, allow_none=False)
    dsn = fields.String(required=True, allow_none=False)
    healthy = fields.Boolean(required=True, allow_none=False)
    errors = fields.List(fields.String, required=True, allow_none=False)


@define_schema
class StatusReportSchema(Schema):
    checkins = fields.Nested(CheckinSchema, many=True, required=True, allow_none=False)
    services = fields.Nested(
        ServiceHealthSchema, many=True, required=True, allow_none=False
    )
