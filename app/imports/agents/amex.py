import typing as t
from functools import cache

from app.config import KEY_PREFIX, Config, ConfigValue
from app.currency import to_pennies
from app.feeds import FeedType
from app.imports.agents.bases.base import PaymentTransactionFields
from app.imports.agents.bases.queue_agent import QueueAgent
from app.matching.agents.registry import matching_agents
from app.streaming.agents.registry import streaming_agents

PROVIDER_SLUG = "amex"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"
AUTH_QUEUE_NAME_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}-auth.queue_name"
SETTLEMENT_QUEUE_NAME_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}-settlement.queue_name"
SCHEDULE_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.schedule"

DATE_FORMAT = "YYYY-MM-DD"
DATETIME_FORMAT = "YYYY-MM-DD-HH.mm.ss"


class AmexAuth(QueueAgent):
    provider_slug = PROVIDER_SLUG
    feed_type = FeedType.AUTH

    config = Config(ConfigValue("queue_name", key=AUTH_QUEUE_NAME_KEY, default="amex-auth"))

    @cache
    def do_not_import(self, merchant_slug: str) -> bool:
        # Use the registered agents from streaming and matching (spotting) to check the merchant
        # If the merchant is a spotting or streaming agent, then do not import, return true for this method
        # Streaming agents checked first since this is less overhead then checking matching agents
        if merchant_slug in streaming_agents:
            return True
        elif merchant_slug in matching_agents:
            # Only stop the spotting merchants from importing.
            match_entry = matching_agents.registered_entries(merchant_slug)
            if "spotted" in match_entry[0]:
                return True

        return False

    def to_transaction_fields(self, data: dict) -> t.Optional[PaymentTransactionFields]:
        transaction_date = self.pendulum_parse(data["transaction_time"], tz="MST")
        amount = to_pennies(data["transaction_amount"])

        merchant_slug = self.get_merchant_slug(data)
        # Spotting and streaming merchants cannot use Amex auth transactions, so do not import.
        if self.do_not_import(merchant_slug):
            return None

        return PaymentTransactionFields(
            merchant_slug=merchant_slug,
            payment_provider_slug=self.provider_slug,
            settlement_key=data["transaction_id"],
            transaction_date=transaction_date,
            has_time=True,
            spend_amount=amount,
            spend_multiplier=100,
            spend_currency="GBP",
            card_token=data["cm_alias"],
            approval_code=data["approval_code"],
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["transaction_id"]

    def get_identifiers(self, data: dict) -> list[str]:
        return [data["merchant_number"]]


class AmexSettlement(QueueAgent):
    provider_slug = PROVIDER_SLUG
    feed_type = FeedType.SETTLED

    config = Config(ConfigValue("queue_name", key=SETTLEMENT_QUEUE_NAME_KEY, default="amex-settlement"))

    def to_transaction_fields(self, data: dict) -> PaymentTransactionFields:
        transaction_date = self.pendulum_parse(data["transactionDate"], tz="Europe/London")
        amount = to_pennies(data["transactionAmount"])

        if data["dpan"]:
            first_six, last_four = data["dpan"].split("XXXXX")
        else:
            first_six, last_four = None, None

        return PaymentTransactionFields(
            merchant_slug=self.get_merchant_slug(data),
            payment_provider_slug=self.provider_slug,
            settlement_key=data["transactionId"],
            transaction_date=transaction_date,
            has_time=True,
            spend_amount=amount,
            spend_multiplier=100,
            spend_currency="GBP",
            card_token=data["cardToken"],
            first_six=first_six,
            last_four=last_four,
            approval_code=data["approvalCode"],
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["transactionId"]

    def get_identifiers(self, data: dict) -> list[str]:
        return [data["merchantNumber"]]
