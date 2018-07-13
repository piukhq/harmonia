from app.api import define_schema
from marshmallow import Schema, fields


@define_schema
class CheckinSchema(Schema):
    datetime = fields.DateTime(required=True)
    human_readable = fields.String(required=True)
    key = fields.String(required=True)
    name = fields.String(required=True)
    seconds_ago = fields.Float(required=True)
    timestamp = fields.Float(required=True)


@define_schema
class StatusReportSchema(Schema):
    checkins = fields.Nested(CheckinSchema, many=True)
