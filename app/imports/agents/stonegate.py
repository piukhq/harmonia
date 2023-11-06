import pendulum

from app.config import KEY_PREFIX, Config, ConfigValue
from app.currency import to_pennies
from app.feeds import FeedType
from app.imports.agents.bases.base import SchemeTransactionFields
from app.imports.agents.bases.queue_agent import QueueAgent

PROVIDER_SLUG = "stonegate"

FIRST_SIX_MAPPING = {("2", "5"): "mastercard", "3": "amex", "4": "visa"}
PAYMENT_CARD_TYPE_MAPPING = {
    ("visa", "vs"): "visa",
    ("mastercard", "mcard", "mc", "master card", "master", "maestro"): "mastercard",
    ("american express", "amex", "americanexpress", "am ex"): "amex"
}


class Stonegate(QueueAgent):
    provider_slug = PROVIDER_SLUG
    feed_type = FeedType.MERCHANT
    payment_card_type = None

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

    def _set_payment_card_type(self, first_six: str, payment_card_type: str):
        if len(first_six) == 6 and first_six[0] in FIRST_SIX_MAPPING:
            self.payment_card_type = FIRST_SIX_MAPPING[first_six[0]]
            return
        for payment_card_option in PAYMENT_CARD_TYPE_MAPPING:
            for payment_card in payment_card_option:
                if payment_card in payment_card_type.lower():
                    self.payment_card_type = PAYMENT_CARD_TYPE_MAPPING[payment_card_option]
                    return

    def _do_import(self, body: dict) -> None:
        self._set_payment_card_type(body["payment_card_first_six"], body["payment_card_type"])
        if not self.payment_card_type:
            self.log.warning(
                f"Discarding transaction {self.get_transaction_id(body)} - unable to get payment card type "
                f"from payment_card_first_six or payment_card_type fields",
            )
            return

        super()._do_import(body)

    def to_transaction_fields(self, data: dict) -> SchemeTransactionFields:
        return SchemeTransactionFields(
            merchant_slug=self.provider_slug,
            payment_provider_slug=self.payment_card_type,
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
