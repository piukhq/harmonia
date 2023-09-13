import pendulum

from app.config import KEY_PREFIX, Config, ConfigValue
from app.currency import to_pennies
from app.feeds import FeedType
from app.imports.agents.bases.base import SchemeTransactionFields
from app.imports.agents.bases.queue_agent import QueueAgent

PROVIDER_SLUG = "costa"


class Costa(QueueAgent):
    provider_slug = PROVIDER_SLUG
    feed_type = FeedType.MERCHANT

    def __init__(self):
        super().__init__()

        # Set up Prometheus metric types
        self.prometheus_metrics = {
            "counters": ["transactions"],
        }

    config = Config(
        ConfigValue(
            "queue_name", key=f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.queue_name", default="tx-costa-harmonia"
        )
    )

    def to_transaction_fields(self, data: dict) -> SchemeTransactionFields:
        return SchemeTransactionFields(
            merchant_slug=self.provider_slug,
            payment_provider_slug=data["payment_card_type"],
            transaction_date=pendulum.instance(data["date"]),
            has_time=True,
            spend_amount=to_pennies(data["amount"]),
            spend_multiplier=100,
            spend_currency=data["currency_code"],
            auth_code=data["auth_code"],
            first_six=data["payment_card_first_six"],
            last_four=data["payment_card_last_four"],
            extra_fields={"metadata": data["metadata"], "items_ordered": data["items_ordered"]},
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["transaction_id"]

    def get_primary_mids(self, data: dict) -> list[str]:
        return [data["merchant_identifier"]]
