import typing as t
from hashlib import sha256

from app.config import KEY_PREFIX, Config, ConfigValue
from app.currency import to_pennies
from app.feeds import FeedType
from app.imports.agents.bases.base import PaymentTransactionFields
from app.imports.agents.bases.queue_agent import QueueAgent

PROVIDER_SLUG = "visa"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"
SCHEDULE_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.schedule"

DATE_FORMAT = "YYYYMMDD"


def _make_settlement_key(key_id: str):
    return sha256(f"visa.{key_id}".encode()).hexdigest()


def get_key_value(data: dict, key: str):
    for d in data["MessageElementsCollection"]:
        if d["Key"] == key:
            return d["Value"]


def try_convert_settlement_mid(mid: str) -> str:
    prefix = "0000000"
    if mid.startswith(prefix):
        return mid[len(prefix) :]
    return mid


class VisaAuth(QueueAgent):
    provider_slug = PROVIDER_SLUG
    feed_type = FeedType.AUTH

    def __init__(self):
        super().__init__()

        # Set up Prometheus metric types
        self.prometheus_metrics = {
            "counters": ["transactions"],
        }

    config = Config(
        ConfigValue(
            "queue_name", key=f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}-auth.queue_name", default="visa-auth"
        )
    )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return get_key_value(data, "Transaction.VipTransactionId")

    def get_mids(self, data: dict) -> t.List[str]:
        return [get_key_value(data, "Transaction.MerchantCardAcceptorId")]

    def to_transaction_fields(self, data: dict) -> PaymentTransactionFields:
        ext_user_id = data["ExternalUserId"]
        transaction_date = self.pendulum_parse(get_key_value(data, "Transaction.TimeStampYYMMDD"), tz="GMT")
        return PaymentTransactionFields(
            merchant_slug=self.get_merchant_slug(data),
            payment_provider_slug=self.provider_slug,
            transaction_date=transaction_date,
            has_time=True,
            spend_amount=to_pennies(get_key_value(data, "Transaction.TransactionAmount")),
            spend_multiplier=100,
            spend_currency="GBP",
            card_token=ext_user_id,
            settlement_key=_make_settlement_key(get_key_value(data, "Transaction.VipTransactionId")),
            auth_code=get_key_value(data, "Transaction.AuthCode"),
        )


class VisaSettlement(QueueAgent):
    provider_slug = PROVIDER_SLUG
    feed_type = FeedType.SETTLED

    def __init__(self):
        super().__init__()

        # Set up Prometheus metric types
        self.prometheus_metrics = {
            "counters": ["transactions"],
        }

    config = Config(
        ConfigValue(
            "queue_name",
            key=f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}-settlement.queue_name",
            default="visa-settlement",
        )
    )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return get_key_value(data, "Transaction.VipTransactionId")

    def get_mids(self, data: dict) -> t.List[str]:
        return [try_convert_settlement_mid(get_key_value(data, "Transaction.MerchantCardAcceptorId"))]

    def to_transaction_fields(self, data: dict) -> PaymentTransactionFields:
        ext_user_id = data["ExternalUserId"]
        transaction_date = self.pendulum_parse(get_key_value(data, "Transaction.MerchantDateTimeGMT"), tz="GMT")
        return PaymentTransactionFields(
            merchant_slug=self.get_merchant_slug(data),
            payment_provider_slug=self.provider_slug,
            transaction_date=transaction_date,
            has_time=True,
            spend_amount=to_pennies(get_key_value(data, "Transaction.SettlementAmount")),
            spend_multiplier=100,
            spend_currency="GBP",
            card_token=ext_user_id,
            settlement_key=_make_settlement_key(get_key_value(data, "Transaction.VipTransactionId")),
            auth_code=get_key_value(data, "Transaction.AuthCode"),
        )


class VisaRefund(QueueAgent):
    provider_slug = PROVIDER_SLUG
    feed_type = FeedType.REFUND

    def __init__(self):
        super().__init__()

        # Set up Prometheus metric types
        self.prometheus_metrics = {
            "counters": ["transactions"],
        }

    config = Config(
        ConfigValue(
            "queue_name",
            key=f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}-refund.queue_name",
            default="visa-refund",
        )
    )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return get_key_value(data, "ReturnTransaction.VipTransactionId")

    def get_mids(self, data: dict) -> t.List[str]:
        return [try_convert_settlement_mid(get_key_value(data, "ReturnTransaction.CardAcceptorIdCode"))]

    def to_transaction_fields(self, data: dict) -> PaymentTransactionFields:
        ext_user_id = data["ExternalUserId"]
        transaction_date = self.pendulum_parse(get_key_value(data, "ReturnTransaction.DateTime"), tz="GMT")
        return PaymentTransactionFields(
            merchant_slug=self.get_merchant_slug(data),
            payment_provider_slug=self.provider_slug,
            transaction_date=transaction_date,
            has_time=True,
            spend_amount=-abs(to_pennies(get_key_value(data, "ReturnTransaction.Amount"))),
            spend_multiplier=100,
            spend_currency="GBP",
            card_token=ext_user_id,
            settlement_key=_make_settlement_key(get_key_value(data, "ReturnTransaction.VipTransactionId")),
            auth_code=get_key_value(data, "ReturnTransaction.AuthCode"),
        )
