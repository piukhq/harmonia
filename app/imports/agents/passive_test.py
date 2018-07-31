from marshmallow import Schema, fields

from app.imports.agents.bases.passive_api_agent import PassiveAPIAgent
from app import models


class PassiveTestAgentSchema(Schema):
    tid = fields.String(required=True)
    value = fields.Integer(required=True)
    card_no = fields.String(required=True)

    @staticmethod
    def to_scheme_transaction(data):
        return models.SchemeTransaction(
            transaction_id=data['tid'],
            pence=data['value'],
            points_earned=None,
            card_id=data['card_no'],
            total_points=None)

    @staticmethod
    def get_transaction_id(data):
        return data['tid']


class PassiveTestAgent(PassiveAPIAgent):
    schema_class = PassiveTestAgentSchema
    provider_slug = 'passive-test-merchant'
