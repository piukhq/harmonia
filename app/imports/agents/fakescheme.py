import inspect

from marshmallow import Schema, fields

from .bases.active_api_agent import ActiveAPIAgent
from app.config import ConfigValue, KEY_PREFIX
from app import models


SCHEDULE = f"{KEY_PREFIX}imports.agents.fake.schedule"


class FakeSchemeCardSchema(Schema):
    class Meta:
        fields = ('balance', 'id',)


class FakeSchemeTransactionSchema(Schema):
    card = fields.Nested(FakeSchemeCardSchema, required=True)

    class Meta:
        fields = ('card', 'id', 'pence', 'points_earned',)

    @staticmethod
    def to_scheme_transaction(data):
        return models.SchemeTransaction(
            transaction_id=data['id'],
            pence=data['pence'],
            points_earned=data['points_earned'],
            card_id=data['card']['id'],
            total_points=data['card']['balance'])


class FakeSchemeAPIAgent(ActiveAPIAgent):
    url = 'http://127.0.0.1:8001/api/transactions'
    schema_class = FakeSchemeTransactionSchema

    class Config:
        schedule = ConfigValue(SCHEDULE, default='* * * * *')

    def help(self):
        return inspect.cleandoc(
            f"""
            This agent works with the dummy loyalty scheme server found in ~/dev/loyaltyscheme.
            It calls /api/transactions on a schedule.
            """)
