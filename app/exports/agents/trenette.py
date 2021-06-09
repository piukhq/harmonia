import typing as t

import pendulum
import settings
from app import db, models
from app.config import KEY_PREFIX, Config, ConfigValue
from app.exports.agents.bases.base import AgentExportData, AgentExportDataOutput
from app.exports.agents.bases.singular_export_agent import SingularExportAgent
from app.service import atlas
from app.service.bpl import BplAPI
from harness.exporters.bpl_mock import BplMockAPI

PROVIDER_SLUG = "bpl-trenette"

BASE_URL_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.base_url"


class Trenette(SingularExportAgent):
    class ReceiptNumberNotFound(Exception):
        pass

    provider_slug = PROVIDER_SLUG
    config = Config(ConfigValue("base_url", key=BASE_URL_KEY, default="http://localhost"))
    loyalty_id = None

    def __init__(self):
        super().__init__()
        if settings.DEBUG:
            self.api_class = BplMockAPI
        else:
            self.api_class = BplAPI

        # Set up Prometheus metric types
        self.prometheus_metrics = {
            "counters": ["receipt_number_not_found", "requests_sent", "failed_requests", "transactions"],
            "histograms": ["request_latency"],
        }

    def get_retry_datetime(self, retry_count: int) -> t.Optional[pendulum.DateTime]:
        if retry_count == 0:
            # first retry in 20 minutes.
            return pendulum.now("UTC") + pendulum.duration(minutes=20)
        elif retry_count <= 6:
            # second retry at 7 AM the next day.
            return self.next_available_retry_time(7)
        else:
            # after the previous seven tries, give up.
            return None

    def next_available_retry_time(self, run_time, timezone="Europe/London") -> t.Optional[pendulum.DateTime]:
        run_time_today = pendulum.now(timezone).at(run_time)
        if run_time_today.is_past():
            return (pendulum.now(timezone) + pendulum.duration(days=1)).at(run_time)
        else:
            return run_time_today

    def make_export_data(self, matched_transaction: models.MatchedTransaction) -> AgentExportData:
        transaction_datetime = pendulum.instance(matched_transaction.transaction_date)
        user_identity = matched_transaction.payment_transaction.user_identity
        self.loyalty_id = user_identity.decrypted_credentials['merchant_identifier']

        return AgentExportData(
            outputs=[
                AgentExportDataOutput(
                    "export.json",
                    {
                        "id": matched_transaction.transaction_id,
                        "transaction_total": matched_transaction.spend_amount,
                        "datetime": transaction_datetime.int_timestamp,
                        "MID": matched_transaction.merchant_identifier.mid,
                        "loyalty_id": self.loyalty_id
                    },
                )
            ],
            transactions=[matched_transaction],
            extra_data={"credentials": matched_transaction.payment_transaction.user_identity.decrypted_credentials},
        )

    def export(
        self, export_data: AgentExportData, *, retry_count: int = 0, session: db.Session
    ) -> atlas.MessagePayload:
        body: dict
        _, body = export_data.outputs[0]  # type: ignore
        api = self.api_class(self.config.get("base_url", session=session), self.provider_slug)
        request_timestamp = pendulum.now().to_datetime_string()
        response = api.post_matched_transaction(body)
        response_timestamp = pendulum.now().to_datetime_string()

        if (200 <= response.status_code <= 299) or (400 <= response.status_code <= 499):
            audit_message = atlas.make_audit_message(
                self.provider_slug,
                atlas.make_audit_transactions(
                    export_data.transactions, tx_loyalty_ident_callback=self.loyalty_id
                ),
                request=body,
                request_timestamp=request_timestamp,
                response=response,
                response_timestamp=response_timestamp,
            )
            return audit_message

        if (300 <= response.status_code <= 399) or (response.status_code >= 500):
            raise Exception("BPL: retry error raised")
