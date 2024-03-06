import csv
import io
import typing as t

import pendulum

from app.config import KEY_PREFIX, Config, ConfigValue
from app.currency import to_pennies
from app.feeds import FeedType
from app.imports.agents.bases.base import SchemeTransactionFields
from app.imports.agents.bases.file_agent import FileAgent
from app.soteria import SoteriaConfigMixin

PROVIDER_SLUG = "itsu"
SCHEDULE_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.schedule"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"


class Itsu(FileAgent, SoteriaConfigMixin):
    feed_type = FeedType.MERCHANT
    provider_slug = PROVIDER_SLUG
    timezone = pendulum.timezone("Europe/London")

    config = Config(
        ConfigValue("path", key=PATH_KEY, default="/"),
        ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *"),
    )

    def __init__(self):
        super().__init__()

        # Set up Prometheus metric types
        self.prometheus_metrics = {
            "counters": ["files_received", "transactions"],
            "gauges": ["last_file_timestamp"],
        }

    def yield_transactions_data(self, data: bytes) -> t.Iterable[dict]:
        fd = io.StringIO(data.decode())
        reader = csv.DictReader(fd)
        for raw_data in reader:
            payment_scheme_is_valid = raw_data["payment_card_type"] in ["visa", "amex", "mastercard"]
            amount_is_eligible = to_pennies(raw_data["amount"]) >= 500

            if payment_scheme_is_valid and amount_is_eligible:
                yield raw_data

    def to_transaction_fields(self, data: dict) -> SchemeTransactionFields:
        return SchemeTransactionFields(
            merchant_slug=self.provider_slug,
            payment_provider_slug=data["payment_card_type"],
            transaction_date=self.get_transaction_date(data),
            has_time=True,
            spend_amount=to_pennies(data["amount"]),
            spend_multiplier=100,
            spend_currency=data["currency_code"],
            auth_code=data["auth_code"],
            first_six=data["payment_card_first_six"],
            last_four=data["payment_card_last_four"],
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["transaction_id"]

    def get_primary_mids(self, data: dict) -> list[str]:
        # TODO: what if we find an unmapped location ID? is raising KeyError acceptable?
        return self.location_id_mid_map[data["retailer_location_id"]]

    def get_transaction_date(self, data: dict) -> pendulum.DateTime:
        return pendulum.parse(data["date"])
