import pendulum

from app.config import KEY_PREFIX, Config, ConfigValue
from app.currency import to_pennies
from app.feeds import FeedType
from app.imports.agents.bases.base import SchemeTransactionFields
from app.imports.agents.bases.queue_agent import QueueAgent

PROVIDER_SLUG = "stonegate"


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

    @staticmethod
    def match_first_six_to_payment_type(first_six: str) -> str:
        if first_six[0] == "4":
            return "visa"
        if first_six[0] in ("2", "5"):
            return "mastercard"
        if first_six[0] == "3":
            return "amex"

    def first_six_valid(self, first_six: str):
        if not bool(first_six and first_six.strip()):
            return False
        if len(first_six) != 6:
            return False
        elif first_six[0] in ("2", "3", "4", "5"):
            self.payment_card_type = self.match_first_six_to_payment_type(first_six)
            return True
        else:
            return False

    def get_payment_card_from_payment_card_type(self, payment_card_type):
        if any(payment_card in payment_card_type.lower() for payment_card in ("visa", "vs")):
            self.payment_card_type = "visa"
        if any(payment_card in payment_card_type.lower() for payment_card in ("mastercard", "mcard", "mc", "master card", "master", "maestro")):
            self.payment_card_type = "mastercard"
        if any(payment_card in payment_card_type.lower() for payment_card in ("american express", "amex", "americanexpress", "am ex")):
            self.payment_card_type = "amex"

    def _do_import(self, body: dict) -> None:
        first_six = body["payment_card_first_six"]
        if not self.first_six_valid(first_six):
            self.get_payment_card_from_payment_card_type(body["payment_card_type"])
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
