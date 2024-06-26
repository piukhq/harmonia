from hashlib import sha256

import pendulum

from app.config import KEY_PREFIX, Config, ConfigValue
from app.currency import to_pennies
from app.feeds import FeedType
from app.imports.agents.bases.base import PaymentTransactionFields
from app.imports.agents.bases.queue_agent import QueueAgent

PROVIDER_SLUG = "visa"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"
SCHEDULE_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.schedule"

DATE_FORMAT = "YYYYMMDD"


def _make_settlement_key(key_id: str) -> str:
    return sha256(f"visa.{key_id}".encode()).hexdigest()


def _get_auth_code(data: dict, transaction_type: str) -> str:
    for d in data["MessageElementsCollection"]:
        if d["Key"] == f"{transaction_type}.AuthCode":
            return d["Value"]

    return ""


def get_key_value(data: dict, key: str) -> str:
    for d in data["MessageElementsCollection"]:
        if d["Key"] == key:
            return d["Value"]

    raise KeyError(f"Key {key} not found in data: {data}")


def try_convert_settlement_mid(mid: str) -> str:
    prefix = "0000000"
    if mid.startswith(prefix):
        return mid[len(prefix) :]
    return mid


def validate_mids(identifiers: list[tuple]) -> list[tuple]:
    # Remove null, "0" or "" identifier values
    return list(
        filter(
            lambda item: item[1] not in [None, "0", ""],
            identifiers,
        )
    )


class VisaAuth(QueueAgent):
    provider_slug = PROVIDER_SLUG
    feed_type = FeedType.AUTH

    timezones = {
        "stonegate": "Europe/London",
        "itsu": "Europe/London",
        "tgi-fridays": "Europe/London",
        "the-works": "Europe/London",
        "viator": "GMT",
        "slim-chickens": "GMT",
    }

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

    def get_primary_mids(self, data: dict) -> list[str]:
        return [get_key_value(data, "Transaction.MerchantCardAcceptorId")]

    def get_secondary_mid(self, data: dict) -> str | None:
        return get_key_value(data, "Transaction.VisaStoreId")

    def get_psimi(self, data: dict) -> str | None:
        return get_key_value(data, "Transaction.VisaMerchantId")

    def to_transaction_fields(self, data: dict) -> PaymentTransactionFields:
        ext_user_id = data["ExternalUserId"]
        return PaymentTransactionFields(
            merchant_slug=self.get_merchant_slug(data),
            payment_provider_slug=self.provider_slug,
            transaction_date=self.get_transaction_date(data),
            has_time=True,
            spend_amount=to_pennies(get_key_value(data, "Transaction.TransactionAmount")),
            spend_multiplier=100,
            spend_currency="GBP",
            card_token=ext_user_id,
            settlement_key=_make_settlement_key(get_key_value(data, "Transaction.VipTransactionId")),
            auth_code=_get_auth_code(data, "Transaction"),
        )

    def get_transaction_date(self, data: dict) -> pendulum.DateTime:
        slug = self.get_merchant_slug(data)
        tz = self.timezones.get(slug, "GMT")
        return self.pendulum_parse(get_key_value(data, "Transaction.TimeStampYYMMDD"), tz=tz)


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

    def get_primary_mids(self, data: dict) -> list[str]:
        return [get_key_value(data, "Transaction.MerchantCardAcceptorId")]

    def get_secondary_mid(self, data: dict) -> str | None:
        return get_key_value(data, "Transaction.VisaStoreId")

    def get_psimi(self, data: dict) -> str | None:
        return get_key_value(data, "Transaction.VisaMerchantId")

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
            auth_code=_get_auth_code(data, "Transaction"),
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

    def get_primary_mids(self, data: dict) -> list[str]:
        return [get_key_value(data, "ReturnTransaction.CardAcceptorIdCode")]

    def get_secondary_mid(self, data: dict) -> str:
        return get_key_value(data, "ReturnTransaction.VisaStoreId")

    def get_psimi(self, data: dict) -> str:
        return get_key_value(data, "ReturnTransaction.VisaMerchantId")

    def to_transaction_fields(self, data: dict) -> PaymentTransactionFields:
        ext_user_id = data["ExternalUserId"]
        transaction_date = pendulum.from_format(
            get_key_value(data, "ReturnTransaction.DateTime"), "M/D/YYYY h:m:s A", tz="GMT"
        )
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
            auth_code=_get_auth_code(data, "ReturnTransaction"),
        )
