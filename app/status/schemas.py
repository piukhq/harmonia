from app.api.app import define_schema
from marshmallow import Schema, fields
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema


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
    connection = fields.Dict(required=True, allow_none=False)
    healthy = fields.Boolean(required=True, allow_none=False)
    errors = fields.List(fields.String, required=True, allow_none=False)


@define_schema
class StatusReportSchema(Schema):
    checkins = fields.Nested(CheckinSchema, many=True, required=True, allow_none=False)
    services = fields.Nested(ServiceHealthSchema, many=True, required=True, allow_none=False)


@define_schema
class ImportTransactionSchema(SQLAlchemyAutoSchema):
    class Meta:
        load_instance = True
        include_relationships = True

    id = fields.Integer(required=True, allow_none=False)
    identified = fields.Boolean(required=True, allow_none=False)
    provider_slug = fields.String(required=True, allow_none=False)
    source = fields.String(required=True, allow_none=False)
    created_at = fields.DateTime(required=True, allow_none=False)


@define_schema
class SchemeTransactionSchema(SQLAlchemyAutoSchema):
    class Meta:
        load_instance = True
        include_relationships = True

    id = fields.Integer(required=True, allow_none=False)
    transaction_date = fields.DateTime(required=True, allow_none=False)
    spend_amount = fields.Integer(required=True, allow_none=False)
    points_amount = fields.Integer(required=True, allow_none=False)
    created_at = fields.DateTime(required=True, allow_none=False)


@define_schema
class PaymentTransactionSchema(SQLAlchemyAutoSchema):
    class Meta:
        load_instance = True
        include_relationships = True

    id = fields.Integer(required=True, allow_none=False)
    transaction_date = fields.DateTime(required=True, allow_none=False)
    spend_amount = fields.Integer(required=True, allow_none=False)
    card_token = fields.String(required=True, allow_none=False)
    created_at = fields.DateTime(required=True, allow_none=False)


@define_schema
class MatchedTransactionSchema(SQLAlchemyAutoSchema):
    class Meta:
        load_instance = True
        include_relationships = True

    id = fields.Integer(required=True, allow_none=False)
    transaction_date = fields.DateTime(required=True, allow_none=False)
    spend_amount = fields.Integer(required=True, allow_none=False)
    points_amount = fields.Integer(required=True, allow_none=False)
    card_token = fields.String(required=True, allow_none=False)
    created_at = fields.DateTime(required=True, allow_none=False)


@define_schema
class ExportTransactionSchema(SQLAlchemyAutoSchema):
    class Meta:
        load_instance = True
        include_relationships = True

    id = fields.Integer(required=True, allow_none=False)
    provider_slug = fields.String(required=True, allow_none=False)
    destination = fields.String(required=True, allow_none=False)
    data = fields.Dict(required=True, allow_none=False)
    created_at = fields.DateTime(required=True, allow_none=False)


@define_schema
class TransactionLookupSchema(Schema):
    class Meta:
        ordered = True

    import_transaction = fields.Nested(ImportTransactionSchema)
    scheme_transaction = fields.Nested(SchemeTransactionSchema)
    payment_transaction = fields.Nested(PaymentTransactionSchema)
    matched_transaction = fields.Nested(MatchedTransactionSchema)
    export_transaction = fields.Nested(ExportTransactionSchema)
