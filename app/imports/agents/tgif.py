import csv
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
        return [
            SchemeTransactionFields(
                merchant_slug=self.provider_slug,
                payment_provider_slug=data["payment_card_type"],
                transaction_date=pendulum.instance(data["date"]),
                has_time=True,
                spend_amount=to_pennies(data["amount"]) + to_pennies(data["gratuity_amount"]),
                spend_multiplier=100,
                spend_currency=data["currency_code"],
                auth_code=data["auth_code"],
                last_four=data["payment_card_last_four"],
                extra_fields={"amount": data["amount"]},
            ),
        ]

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["transaction_id"]

    def get_primary_mids(self, data: dict) -> list[str]:
        return [data["merchant_identifier"]]
