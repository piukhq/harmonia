import pendulum

from app.config import KEY_PREFIX, Config, ConfigValue
from app.currency import to_pennies
from app.feeds import FeedType
from app.imports.agents.bases.base import (
    SchemeTransactionFields,
    get_mapped_payment_provider,
    get_payment_provider_from_first_six,
)
from app.imports.agents.bases.queue_agent import QueueAgent

PROVIDER_SLUG = "stonegate"

PAYMENT_CARD_TYPE_MAPPING = {
    "visa": ["visa", "vs"],
    "mastercard": ["mastercard", "mcard", "mc", "master card", "master", "maestro"],
    "amex": ["american express", "amex", "americanexpress", "am ex"],
}


class Stonegate(QueueAgent):
    provider_slug = PROVIDER_SLUG
    feed_type = FeedType.MERCHANT

    config = Config(
        ConfigValue(
            "queue_name",
            key=f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.queue_name",
            default="tx-stonegate-harmonia",
        ),
    )

    def __init__(self):
        super().__init__()

        # Set up Prometheus metric types
        self.prometheus_metrics = {
            "counters": ["transactions"],
        }

    @staticmethod
    def _get_payment_card_type(first_six: str, payment_card_type: str) -> str | None:
        if payment_provider := get_payment_provider_from_first_six(first_six):
            return payment_provider
        else:
            return get_mapped_payment_provider(payment_card_type, PAYMENT_CARD_TYPE_MAPPING)

    def _do_import(self, body: dict) -> None:
        payment_card_type = self._get_payment_card_type(body["payment_card_first_six"], body["payment_card_type"])
        if not payment_card_type:
            self.log.warning(
                f"Discarding transaction {self.get_transaction_id(body)} - unable to get payment card type "
                f"from payment_card_first_six or payment_card_type fields",
            )
            return

        body["payment_card_type"] = payment_card_type

        super()._do_import(body)

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
            extra_fields={"account_id": data["metadata"]["AccountID"]},
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["transaction_id"]

    def get_primary_mids(self, data: dict) -> list[str]:
        return self.location_id_mid_map[data["retailer_location_id"]]
