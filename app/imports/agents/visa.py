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


def get_valid_identifiers(data: dict, identifier_mapping: dict):
    ids = {
        "PRIMARY": get_key_value(data, identifier_mapping["PRIMARY"]),
        "SECONDARY": get_key_value(data, identifier_mapping["SECONDARY"]),
        "PSIMI": get_key_value(data, identifier_mapping["PSIMI"]),
    }
    # Remove empty strings
    ids = {k: v for k, v in ids.items() if v}
    return ids


class VisaAuth(QueueAgent):
    provider_slug = PROVIDER_SLUG
    feed_type = FeedType.AUTH
    IDENTIFIER_TYPE_TO_IDENTIFIER_MAPPING = {
        "PRIMARY": "Transaction.MerchantCardAcceptorId",
        "SECONDARY": "Transaction.VisaStoreId",
        "PSIMI": "Transaction.VisaMerchantId",
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

    def get_transaction_id(self, data):
        return get_key_value(data, "Transaction.VipTransactionId")

    def get_identifiers_from_data(self, data: dict) -> dict:
        return get_valid_identifiers(data, self.IDENTIFIER_TYPE_TO_IDENTIFIER_MAPPING)

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
    IDENTIFIER_TYPE_TO_IDENTIFIER_MAPPING = {
        "PRIMARY": "Transaction.MerchantCardAcceptorId",
        "SECONDARY": "Transaction.VisaStoreId",
        "PSIMI": "Transaction.VisaMerchantId",
    }

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

    def get_identifiers_from_data(self, data: dict) -> dict:
        return get_valid_identifiers(data, self.IDENTIFIER_TYPE_TO_IDENTIFIER_MAPPING)

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
    IDENTIFIER_TYPE_TO_IDENTIFIER_MAPPING = {
        "PRIMARY": "ReturnTransaction.CardAcceptorIdCode",
        "SECONDARY": "ReturnTransaction.VisaStoreId",
        "PSIMI": "ReturnTransaction.VisaMerchantId",
    }

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

    def get_identifiers_from_data(self, data: dict) -> dict:
        return get_valid_identifiers(data, self.IDENTIFIER_TYPE_TO_IDENTIFIER_MAPPING)

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
            auth_code=get_key_value(data, "ReturnTransaction.AuthCode"),
        )
