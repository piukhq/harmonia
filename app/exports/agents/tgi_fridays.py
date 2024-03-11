from decimal import ROUND_HALF_UP, Decimal

import pendulum
from blinker import signal

from app import db, models
from app.config import KEY_PREFIX, Config, ConfigValue
from app.currency import to_pennies
from app.exports.agents.bases.base import AgentExportData, AgentExportDataOutput, ExportDelayRetry
from app.exports.agents.bases.singular_export_agent import SingularExportAgent
from app.reporting import sanitise_logs
from app.service import atlas, tgi_fridays

PROVIDER_SLUG = "tgi-fridays"

BASE_URL_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.base_url"
EXPORT_DELAY_SECONDS = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.delay_seconds"
DEFAULT_POINT_CONVERSION_RATE_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.default_point_conversion_rate"

MAX_RETRY_COUNT = 7


class TGIFridays(SingularExportAgent):
    provider_slug = PROVIDER_SLUG
    config = Config(
        ConfigValue("base_url", key=BASE_URL_KEY, default="https://reflector.staging.gb.bink.com/mock/"),
        ConfigValue("delay_seconds", key=EXPORT_DELAY_SECONDS, default="86400"),
        ConfigValue("default_point_conversion_rate", key=DEFAULT_POINT_CONVERSION_RATE_KEY, default="1"),
    )

    def __init__(self):
        super().__init__()
        self.api_class = tgi_fridays.TGIFridaysAPI

        # Set up Prometheus metric types
        self.prometheus_metrics = {
            "counters": ["requests_sent", "failed_requests", "transactions"],
            "histograms": ["request_latency"],
        }

    @staticmethod
    def get_loyalty_identifier(export_transaction: models.ExportTransaction) -> str:
        return export_transaction.decrypted_credentials["merchant_identifier"]

    def get_retry_datetime(self, retry_count: int, *, exception: Exception | None = None) -> pendulum.DateTime | None:
        if isinstance(exception, ExportDelayRetry):
            return pendulum.now().add(seconds=exception.delay_seconds)

        # account for initial delay, act as if the second retry is actually the first
        retry_count = max(0, retry_count - 1)

        if retry_count == 0:
            # first retry in 20 minutes.
            return pendulum.now() + pendulum.duration(minutes=20)
        elif retry_count <= MAX_RETRY_COUNT:
            # second+ retry at 10 AM the next day.
            return self.next_available_retry_time(10)
        else:
            # after the previous MAX_RETRY_COUNT tries, give up.
            return None

    def should_send_export(
        self, export_transaction: models.ExportTransaction, retry_count: int, session: db.Session
    ) -> bool:
        if export_transaction:
            if retry_count == 0:
                delay_seconds = int(self.config.get("delay_seconds", session=session))
                transaction_date = pendulum.instance(export_transaction.transaction_date)
                transaction_time_diff = pendulum.now().diff(transaction_date).in_seconds()
                if transaction_time_diff <= delay_seconds:
                    # calculate the delay required, if less than 60 seconds, default to 60 seconds
                    delay = max(60, delay_seconds - transaction_time_diff)
                    raise ExportDelayRetry(delay_seconds=delay)

        # Perform dedupe process after 24 hours delay
        api = self.api_class(self.config.get("base_url", session=session))
        historical_rewarded_transactions = api.transaction_history(export_transaction)
        return self.exportable_transaction(export_transaction, historical_rewarded_transactions)

    def make_export_data(self, export_transaction: models.ExportTransaction, session: db.Session) -> AgentExportData:
        points_rate = int(self.config.get("default_point_conversion_rate", session=session))
        amount = export_transaction.extra_fields["amount"]
        points = int(Decimal(amount).to_integral_value(rounding=ROUND_HALF_UP)) * points_rate
        return AgentExportData(
            outputs=[
                AgentExportDataOutput(
                    "export.json",
                    {
                        "user_id": self.get_loyalty_identifier(export_transaction),
                        "message": "You’ve been awarded stripes",
                        "gift_count": points,
                        "location_id": export_transaction.location_id,
                    },
                )
            ],
            transactions=[export_transaction],
            extra_data=export_transaction.extra_fields,
        )

    def export(self, export_data: AgentExportData, *, retry_count: int = 0, session: db.Session) -> None:
        body: dict
        _, body = export_data.outputs[0]  # type: ignore

        api = self.api_class(self.config.get("base_url", session=session))
        request_timestamp = pendulum.now().to_datetime_string()
        response = api.transactions(body)
        response_timestamp = pendulum.now().to_datetime_string()

        atlas.queue_audit_message(
            atlas.make_audit_message(
                self.provider_slug,
                atlas.make_audit_transactions(
                    export_data.transactions, tx_loyalty_ident_callback=lambda tx: tx.loyalty_id
                ),
                request=sanitise_logs(body, self.provider_slug),
                request_timestamp=request_timestamp,
                response=response,
                response_timestamp=response_timestamp,
                request_url=response.url,
                retry_count=retry_count,
            )
        )
        response.raise_for_status()

    def exportable_transaction(
        self, export_transaction: models.ExportTransaction, historical_rewarded_transactions: list[dict]
    ) -> bool:
        """
        Check if the current transaction has already been rewarded in the historical transactions.
        """
        # Check for errors in the response
        if not historical_rewarded_transactions:
            return False

        for transaction in historical_rewarded_transactions:
            if not transaction["receipt_amount"] or not transaction["receipt_date"]:
                continue
            amount = to_pennies(export_transaction.extra_fields["amount"])
            history_spend_amount = to_pennies(transaction["receipt_amount"])
            amount_match = amount == history_spend_amount

            time_tolerance = 60 * 15  # 15 minutes
            current_tx_date = pendulum.instance(export_transaction.transaction_date)
            history_tx_date = pendulum.parse(transaction["receipt_date"])
            history_tx_date_max = history_tx_date.add(seconds=time_tolerance)
            history_tx_date_min = history_tx_date.subtract(seconds=time_tolerance)
            dates_match = history_tx_date_min <= current_tx_date <= history_tx_date_max

            # we don't export the transactionm if the points and dates match
            if amount_match and dates_match:
                signal("unexported-transaction").send(self, transactions=[export_transaction])
                return False

        return True
