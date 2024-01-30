import csv
from hashlib import sha256
import io
import typing as t

import pendulum

from app.config import KEY_PREFIX, Config, ConfigValue
from app.currency import to_pennies
from app.feeds import FeedType
from app.imports.agents.bases.base import SchemeTransactionFields
from app.imports.agents.bases.file_agent import FileAgent

PROVIDER_SLUG = "tgi-fridays"
SCHEDULE_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.schedule"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"

DATE_FORMAT = "YYYYMMDD"
TIME_FORMAT = "HHmm"
DATETIME_FORMAT = f"{DATE_FORMAT} {TIME_FORMAT}"


def make_transaction_id(*,  transaction_date: pendulum.DateTime, identifier: str, amount: str):
    hash_parts = [
        transaction_date.date().isoformat(),
        identifier,
        amount,
    ]
    return sha256(f".{'.'.join(hash_parts)}".encode()).hexdigest()


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

    def yield_transactions_data(self, data: bytes) -> t.Iterable[dict]:
        fd = io.StringIO(data.decode())
        reader = csv.DictReader(fd)
        for raw_data in reader:
            payment_scheme_is_valid = raw_data["payment_card_type"] in ["visa", "amex", "mastercard"]

            if payment_scheme_is_valid:
                yield raw_data

    def to_transaction_fields(self, data: dict) -> list[SchemeTransactionFields]:
        transaction_date = self.get_transaction_date(data)
        return [
            SchemeTransactionFields(
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
            ),
        ]

    def get_transaction_id(self, data: dict) -> str:
        return make_transaction_id(
                    transaction_date=self.get_transaction_date(data),
                    identifier=data["merchant_identifier"],
                    amount=data["amount"]
                )

    def get_primary_mids(self, data: dict) -> list[str]:
        return [data["merchant_identifier"]]

    def get_transaction_date(self, data: dict) -> pendulum.DateTime:
        return pendulum.parse(data["date"])
