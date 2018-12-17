import inspect
from datetime import datetime
from decimal import Decimal

from marshmallow import Schema, fields

from app import models
from app.config import KEY_PREFIX, ConfigValue
from app.imports.agents.bases.active_api_agent import ActiveAPIAgent

SCHEDULE_KEY = f"{KEY_PREFIX}imports.agents.fake.schedule"

PROVIDER_SLUG = "fake"


class FakeSchemeTransactionSchema(Schema):
    amount = fields.String()
    earned = fields.String()
    id = fields.String()
    merchant_id = fields.String()
    occurred_on = fields.String()

    @staticmethod
    def to_scheme_transaction(data):
        spend_parts = data["amount"].split(" ")
        return models.SchemeTransaction(
            provider_slug=PROVIDER_SLUG,
            mid=data["merchant_id"],
            transaction_id=data["id"],
            transaction_date=datetime.strptime(
                data["occurred_on"], "%a, %d %b %Y %H:%M:%S %Z"
            ),
            spend_amount=int(Decimal(spend_parts[0]) * 100),
            spend_multiplier=100,
            spend_currency=spend_parts[1].upper(),
            points_amount=data["points_earned"],
            points_multiplier=1,
            extra_fields={},
        )

    @staticmethod
    def get_transaction_id(data):
        return data["id"]


class FakeSchemeAPIAgent(ActiveAPIAgent):
    url = "http://127.0.0.1:41234/transactions"
    schema_class = FakeSchemeTransactionSchema
    provider_slug = PROVIDER_SLUG

    class Config:
        schedule = ConfigValue(SCHEDULE_KEY, default="* * * * *")

    def help(self):
        return inspect.cleandoc(
            f"""
            This agent calls {self.url} on a schedule of {self.Config.schedule}
            """
        )
