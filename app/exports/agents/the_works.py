import uuid
from decimal import Decimal

import pendulum
import sentry_sdk
from blinker import signal

from app import db, models
from app.config import KEY_PREFIX, Config, ConfigValue
from app.currency import to_pounds
from app.exports.agents.bases.base import AgentExportData, AgentExportDataOutput
from app.exports.agents.bases.singular_export_agent import SingularExportAgent
from app.reporting import sanitise_logs
from app.service import atlas, the_works

PROVIDER_SLUG = "the-works"

BASE_URL_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.base_url"
FAILOVER_URL_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.failover_url"
PROMO_POINT_CONVERSION_RATE_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.promo_point_conversion_rate"
DEFAULT_POINT_CONVERSION_RATE_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.default_point_conversion_rate"
PROMOTION_START_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.promotion_start"
PROMOTION_END_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.promotion_end"


class DedupeDelayRetry(Exception):
    def __init__(self, delay_seconds: int = 5, *args: object) -> None:
        self.delay_seconds = delay_seconds
        super().__init__(*args)


class TheWorks(SingularExportAgent):
    provider_slug = PROVIDER_SLUG
    config = Config(
        ConfigValue("base_url", key=BASE_URL_KEY, default="https://reflector.staging.gb.bink.com/mock/"),
        ConfigValue("failover_url", key=FAILOVER_URL_KEY, default="https://reflector.staging.gb.bink.com/mock/"),
        ConfigValue("default_point_conversion_rate", key=DEFAULT_POINT_CONVERSION_RATE_KEY, default="5"),
        ConfigValue("promo_point_conversion_rate", key=PROMO_POINT_CONVERSION_RATE_KEY, default="5"),
        ConfigValue("promotion_start", key=PROMOTION_START_KEY, default=""),
        ConfigValue("promotion_end", key=PROMOTION_END_KEY, default=""),
    )

    def get_retry_datetime(self, retry_count: int, *, exception: Exception | None = None) -> pendulum.DateTime | None:
        if isinstance(exception, DedupeDelayRetry):
            return pendulum.now().add(seconds=exception.delay_seconds)

        # we account for the original dedupe delay by decrementing the retry
        # count to essentially act as if the second retry is actually the first.
        return super().get_retry_datetime(retry_count - 1, exception=exception)

    def find_export_transaction(
        self, pending_export: models.PendingExport, *, session: db.Session
    ) -> models.ExportTransaction:
        # Get the saved transaction for export and compare to the works historical transactions
        matched_transaction = super().find_export_transaction(pending_export, session=session)

        if matched_transaction:
            # The Works export transaction process requires a check against known rewarded transactions
            # This means we need to request a transaction history from The Works, the compare
            # the current transaction with the works transactions.
            api = the_works.TheWorksAPI(self.config.get("base_url", session), self.config.get("failover_url", session))
            # Get transactions history from GiveX The Works.
            historical_rewarded_transactions = api.transaction_history(matched_transaction, PROVIDER_SLUG)
            if not self.exportable_transaction(matched_transaction, historical_rewarded_transactions, session):
                self.log.warning("Transaction has already been rewarded in The Works - GiveX system.")
                raise db.NoResultFound

        return matched_transaction

    def make_export_data(self, export_transaction: models.ExportTransaction, session: db.Session) -> AgentExportData:
        api = the_works.TheWorksAPI(self.config.get("base_url", session), self.config.get("failover_url", session))
        user_id, password = api.get_credentials()
        transaction_code = str(uuid.uuid4())
        method = "dc_911" if export_transaction.spend_amount > 0 else "dc_945"
        amount = abs(export_transaction.spend_amount)
        return AgentExportData(
            outputs=[
                AgentExportDataOutput(
                    "export.json",
                    {
                        "jsonrpc": "2.0",
                        "method": method,
                        "id": 1,
                        "params": [
                            "en",  # language code
                            transaction_code,
                            user_id,
                            password,
                            export_transaction.loyalty_id,  # givex number
                            to_pounds(amount),
                        ],
                    },
                )
            ],
            transactions=[export_transaction],
            extra_data=export_transaction.extra_fields,
        )

    def export(self, export_data: AgentExportData, *, retry_count: int = 0, session: db.Session) -> None:
        if retry_count == 0:
            created_at = pendulum.instance(export_data.transactions[0].created_at)
            if pendulum.now().diff(created_at).total_seconds() < 5:
                raise DedupeDelayRetry

        body: dict
        _, body = export_data.outputs[0]  # type: ignore

        api = the_works.TheWorksAPI(self.config.get("base_url", session), self.config.get("failover_url", session))

        request_timestamp = pendulum.now().to_datetime_string()
        response = api.transactions(body, "")
        response_timestamp = pendulum.now().to_datetime_string()

        request_url = api.base_url
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
        self, matched_transaction: models.ExportTransaction, historical_rewarded_transactions: dict, session: db.Session
    ):
        """
        Check if the current transactions has already been rewarded in the historical transactions.
        """

        # Check for errors in the response
        if historical_rewarded_transactions["result"] and int(historical_rewarded_transactions["result"][1]) > 0:
            return False

        is_refund = matched_transaction.spend_amount < 0

        points_rate = self.point_conversion_rate(session)

        for transaction in historical_rewarded_transactions["result"][5]:
            current_tx_points = int(Decimal(matched_transaction.spend_amount) / 100) * points_rate
            history_points = int(Decimal(transaction[3]))  # Should be the points
            points_match = current_tx_points == history_points

            current_tx_date = pendulum.instance(matched_transaction.transaction_date).to_date_string()
            history_tx_date = pendulum.parse(transaction[0]).to_date_string()  # Date part only.
            dates_match = current_tx_date == history_tx_date

            # there are two cases in which we can't export the transaction:
            # 1. the transaction is not a refund, and the points and dates both match
            # 2. the transaction is a refund, and the points match (dates are irrelevant)
            if points_match and (is_refund or dates_match):
                signal("unexported-transaction").send(self, transactions=[matched_transaction])
                return False

        return True

    def point_conversion_rate(self, session: db.Session) -> int:
        """
        The Works want to award more points during a promotion period.
        Using harmonia's configuration service to set default and promotional point rates
        alongside promotion start and end dates.
        point conversion rates default = 5 outside of promotional periods
        Jira ticket RET-2508
        """
        promotion_start = self.config.get("promotion_start", session=session)
        promotion_end = self.config.get("promotion_end", session=session)
        points_rate = int(self.config.get("default_point_conversion_rate", session=session))
        if promotion_start and promotion_end:
            try:
                start_promo = pendulum.parse(promotion_start, tz="Europe/London").start_of("day")
                end_promo = pendulum.parse(promotion_end, tz="Europe/London").end_of("day")
                date_now = pendulum.now(tz="Europe/London")
                if start_promo <= date_now <= end_promo:
                    points_rate = int(self.config.get("promo_point_conversion_rate", session=session))
                    self.log.info(
                        f"The Works promotion: starting: {start_promo}; ending: {end_promo}; rate: {points_rate}"
                    )
                else:
                    self.log.info(
                        f"The works promotion period may have ended or configured dates are not valid"
                        f"starting: {start_promo}; ending: {end_promo}; rate: {points_rate}"
                    )
            except (pendulum.parsing.exceptions.ParserError, ValueError) as ex:
                sentry_sdk.capture_exception(ex)

        return points_rate
