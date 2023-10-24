import pendulum

from app.config import KEY_PREFIX, Config, ConfigValue
from app.currency import to_pennies
from app.feeds import FeedType
from app.imports.agents.bases.base import SchemeTransactionFields
from app.imports.agents.bases.queue_agent import QueueAgent

PROVIDER_SLUG = "stonegate"

PAYMENT_CARD_TYPES = {"VS": "visa", "MC": "mastercard", "AX": "amex"}


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

    def first_six_valid(self, txid: str, first_six: str):
        if len(first_six) != 6:
            self.log.warning(
                f"Discarding transaction {txid} as the payment_card_first_six field does not contain 6 characters",
            )
            return False
        elif first_six[0] in ("2", "3", "4", "5"):
            return True
        else:
            self.log.warning(
                f"Discarding transaction {txid} as the payment_card_first_six is not recognised",
            )
            return False

    def _do_import(self, body: dict) -> None:
        txid = self.get_transaction_id(body)
        first_six = body["payment_card_first_six"]
        if not bool(first_six and first_six.strip()):
            self.log.warning(
                f"Discarding transaction {txid} as the payment_card_first_six field is empty",
            )
            return
        if not self.first_six_valid(txid, first_six):
            return

        super()._do_import(body)

    @staticmethod
    def match_first_six_to_payment_type(first_six: str) -> str:
        if first_six[0] == "4":
            return "visa"
        elif first_six[0] in ("2", "5"):
            return "mastercard"
        else:
            return "amex"

    def to_transaction_fields(self, data: dict) -> SchemeTransactionFields:
        return SchemeTransactionFields(
            merchant_slug=self.provider_slug,
            payment_provider_slug=self.match_first_six_to_payment_type(data["payment_card_first_six"]),
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
