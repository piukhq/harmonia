import csv
import io
import typing as t
from hashlib import sha256

import pendulum

from app.config import KEY_PREFIX, Config, ConfigValue
from app.currency import to_pennies
from app.feeds import FeedType
from app.imports.agents.bases.base import (
    SchemeTransactionFields,
    get_mapped_payment_provider,
    get_payment_provider_from_first_six,
)
from app.imports.agents.bases.file_agent import FileAgent

PROVIDER_SLUG = "tgi-fridays"
SCHEDULE_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.schedule"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"

PAYMENT_CARD_TYPE_MAPPING = {
    "visa": ["visa", "vs"],
    "mastercard": ["mastercard", "mcard", "mc", "master card", "master", "maestro"],
    "amex": ["american express", "amex", "americanexpress", "am ex"],
}


def make_transaction_id(
    *, transaction_date: pendulum.DateTime, identifier: str, amount: str, transaction_id: str, gratuity_amount: str
):
    hash_parts = [
        transaction_date,
        identifier,
        amount,
        transaction_id,
        gratuity_amount,
    ]
    return sha256(".".join(hash_parts).encode()).hexdigest()


class TGIFridays(FileAgent):
    provider_slug = PROVIDER_SLUG
    feed_type = FeedType.MERCHANT

    config = Config(
        ConfigValue("path", key=PATH_KEY, default="/"),
        ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *"),
    )

    def __init__(self):
        super().__init__()

        # Set up Prometheus metric types
        self.prometheus_metrics = {"counters": ["files_received", "transactions"], "gauges": ["last_file_timestamp"]}

    @staticmethod
    def _get_payment_card_type(first_six: str, payment_card_type: str) -> str | None:
        if payment_provider := get_payment_provider_from_first_six(first_six):
            return payment_provider
        else:
            return get_mapped_payment_provider(payment_card_type, PAYMENT_CARD_TYPE_MAPPING)

    def yield_transactions_data(self, data: bytes) -> t.Iterable[dict]:
        fd = io.StringIO(data.decode())
        reader = csv.DictReader(fd)
        for raw_data in reader:
            payment_card_type = self._get_payment_card_type(
                raw_data["payment_card_first_six"], raw_data["payment_card_type"]
            )
            raw_data["payment_card_type"] = payment_card_type

            if payment_card_type:
                yield raw_data

    def to_transaction_fields(self, data: dict) -> SchemeTransactionFields:
        return SchemeTransactionFields(
            merchant_slug=self.provider_slug,
            payment_provider_slug=data["payment_card_type"],
            has_time=True,
            spend_amount=to_pennies(data["amount"]) + to_pennies(data["gratuity_amount"]),
            spend_multiplier=100,
            spend_currency=data["currency_code"],
            auth_code=data["auth_code"],
            transaction_date=self.get_transaction_date(data),
            first_six=data["payment_card_first_six"],
            last_four=data["payment_card_last_four"],
            extra_fields={"amount": data["amount"]},
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return make_transaction_id(
            transaction_date=data["date"],
            identifier=data["merchant_identifier"],
            amount=data["amount"],
            transaction_id=data["transaction_id"],
            gratuity_amount=data["gratuity_amount"],
        )

    def get_primary_mids(self, data: dict) -> list[str]:
        return [data["merchant_identifier"]]

    def get_transaction_date(self, data: dict) -> pendulum.DateTime:
        return pendulum.parse(data["date"])
