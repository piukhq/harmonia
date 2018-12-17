import os

from marshmallow import Schema, fields

from app.imports.agents.bases.passive_api_agent import PassiveAPIAgent
from app import models

PROVIDER_SLUG = "passive-test-merchant"


class PassiveTestAgentSchema(Schema):
    tid = fields.String(required=True)
    mid = fields.String(required=True)
    date = fields.DateTime(required=True)
    spend = fields.Decimal(required=True)
    pts = fields.Integer(required=True)

    @staticmethod
    def to_scheme_transaction(data):
        return models.SchemeTransaction(
            provider_slug=PROVIDER_SLUG,
            mid=data["mid"],
            transaction_id=data["tid"],
            transaction_date=data["date"],
            spend_amount=int(data["spend"] * 100),
            spend_multiplier=100,
            spend_currency="GBP",
            points_amount=data["pts"],
            points_multiplier=1,
            extra_fields={},
        )

    @staticmethod
    def get_transaction_id(data):
        return data["tid"]


class PassiveTestAgent(PassiveAPIAgent):
    schema_class = PassiveTestAgentSchema
    provider_slug = PROVIDER_SLUG

    def help(self):
        return self._help(
            module=self.__module__, wsgi_file=os.path.relpath(__file__, os.curdir)
        )

    def extract_transactions(self, request_json):
        return request_json["transactions"]


app = PassiveTestAgent().create_app()
