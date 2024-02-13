from decimal import ROUND_HALF_UP, Decimal

import pendulum
from blinker import signal

from app import db, models
from app.config import KEY_PREFIX, Config, ConfigValue
from app.exports.agents.bases.base import AgentExportData, AgentExportDataOutput, ExportDelayRetry
from app.exports.agents.bases.singular_export_agent import SingularExportAgent
from app.reporting import sanitise_logs
from app.service import atlas, tgi_fridays

PROVIDER_SLUG = "tgi-fridays"

BASE_URL_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.base_url"
EXPORT_DELAY_SECONDS = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.delay_seconds"
DEFAULT_POINT_CONVERSION_RATE_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.default_point_conversion_rate"


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

        # we account for the original dedupe delay by decrementing the retry
        # count to essentially act as if the second retry is actually the first.
        return super().get_retry_datetime(retry_count - 1, exception=exception)

    def should_send_export(
        self, export_transaction: models.ExportTransaction, retry_count: int, session: db.Session
    ) -> bool:
        if export_transaction:
            if retry_count == 0:
                delay_seconds = int(self.config.get("delay_seconds", session=session))
                created_at = pendulum.instance(export_transaction.transactions[0].created_at)
                if pendulum.now().diff(created_at).in_hours() < delay_seconds:
                    raise ExportDelayRetry(delay_seconds=delay_seconds)

        # Perform dedupe process after 24 hours delay
        historical_rewarded_transactions = self.api_class.transaction_history(export_transaction, PROVIDER_SLUG)
        return self.exportable_transaction(export_transaction, historical_rewarded_transactions)

    def make_export_data(self, export_transaction: models.ExportTransaction, session: db.Session) -> AgentExportData:
        points_rate = int(self.config.get("default_point_conversion_rate", session=session))
        spend_amount = export_transaction.spend_amount
        points = int(Decimal(spend_amount).to_integral_value(rounding=ROUND_HALF_UP)) * points_rate
        return AgentExportData(
            outputs=[
                AgentExportDataOutput(
                    "export.json",
                    {
                        "user_id": self.get_loyalty_identifier(export_transaction),
                        "subject": "Gifts from us",
                        "message": "You’ve been awarded stripes",
                        "gift_reason": "reason",
                        "gift_count": points,
                        "location_id": export_transaction.mid,
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
        endpoint = "/api2/dashboard/users/support"
        request_timestamp = pendulum.now().to_datetime_string()
        response = api.transactions(body, endpoint)
        response_timestamp = pendulum.now().to_datetime_string()

        request_url = self.api_class.base_url
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
                request_url=request_url,
                retry_count=retry_count,
            )
        )
        response.raise_for_status()

    def exportable_transaction(
        self, export_transaction: models.ExportTransaction, historical_rewarded_transactions: dict
    ) -> bool:
        """
        Check if the current transaction has already been rewarded in the historical transactions.
        """
        # Check for errors in the response
        if historical_rewarded_transactions["result"] and int(historical_rewarded_transactions["result"][1]) > 0:
            return False

        for transaction in historical_rewarded_transactions:
            spend_amount = export_transaction.spend_amount
            history_spend_amount = int(Decimal(transaction["receipt_amount"]))
            amount_match = spend_amount == history_spend_amount

            time_tolerance = 60 * 3
            current_tx_date = pendulum.instance(export_transaction.transaction_date).to_date_string()
            history_tx_date = pendulum.parse(transaction["receipt_date"])
            history_tx_date_max = history_tx_date.add(time_tolerance)
            history_tx_date_min = history_tx_date.subtract(time_tolerance)
            dates_match = history_tx_date_min >= current_tx_date <= history_tx_date_max

            # there are two cases in which we can't export the transaction:
            # 1. the transaction is not a refund, and the points and dates both match
            # 2. the transaction is a refund, and the points match (dates are irrelevant)
            if amount_match and dates_match:
                signal("unexported-transaction").send(self, transactions=[export_transaction])
                return False

        return True
