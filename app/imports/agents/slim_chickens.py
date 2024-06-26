import pendulum

from app import db
from app.config import KEY_PREFIX, Config, ConfigValue
from app.feeds import FeedType
from app.imports.agents.bases.base import SchemeTransactionFields
from app.imports.agents.bases.queue_agent import QueueAgent

PROVIDER_SLUG = "slim-chickens"

PAYMENT_CARD_TYPES = {
    "visa debit": "visa",
    "visa": "visa",
    "mastercard": "mastercard",
    "debit mastercard": "mastercard",
}


class SlimChickens(QueueAgent):
    provider_slug = PROVIDER_SLUG
    feed_type = FeedType.MERCHANT

    config = Config(
        ConfigValue(
            "queue_name",
            key=f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.queue_name",
            default="tx-slim-chickens-harmonia",
        ),
        ConfigValue(
            "spend_threshold",
            key=f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.spend_threshold",
            default="750",
        ),
    )

    def __init__(self):
        super().__init__()

        # Set up Prometheus metric types
        self.prometheus_metrics = {
            "counters": ["transactions"],
        }

    def _do_import(self, body: dict) -> None:
        txid = self.get_transaction_id(body)

        is_supported_card_type = body["payment_card_type"].casefold() in PAYMENT_CARD_TYPES

        if not is_supported_card_type:
            supported_types = ", ".join(key.title() for key in PAYMENT_CARD_TYPES.keys())
            self.log.warning(
                f"Discarding transaction {txid} due to unsupported payment card type {body['payment_card_type']!r}, "
                f"expected one of: {supported_types} (case insensitive)",
            )
            return

        with db.session_scope() as session:
            spend_threshold = int(self.config.get("spend_threshold", session=session))

        is_eligible_amount = body["amount"] >= spend_threshold

        if not is_eligible_amount:
            self.log.warning(
                f"Discarding transaction {txid} due to ineligible amount {body['amount']!r}, "
                f"expected >= {spend_threshold!r}",
            )
            return

        super()._do_import(body)

    def to_transaction_fields(self, data: dict) -> SchemeTransactionFields:
        return SchemeTransactionFields(
            merchant_slug=self.provider_slug,
            payment_provider_slug=PAYMENT_CARD_TYPES[data["payment_card_type"].casefold()],
            transaction_date=pendulum.instance(data["date"]),
            has_time=True,
            spend_amount=data["amount"],
            spend_multiplier=100,
            spend_currency=data["currency_code"],
            auth_code=data["auth_code"],
            last_four=data["payment_card_last_four"],
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["transaction_id"]

    def get_primary_mids(self, data: dict) -> list[str]:
        return self.location_id_mid_map[data["retailer_location_id"]]
