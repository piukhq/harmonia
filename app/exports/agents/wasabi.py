import hashlib
import typing as t

import pendulum
from requests import RequestException, Response

import settings
from app import db, models
from app.config import KEY_PREFIX, Config, ConfigValue
from app.exports.agents.bases.base import AgentExportData, AgentExportDataOutput
from app.exports.agents.bases.singular_export_agent import SingularExportAgent
from app.service import atlas
from app.service.acteol import ActeolAPI
from harness.exporters.acteol_mock import ActeolMockAPI

PROVIDER_SLUG = "wasabi-club"

BASE_URL_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.base_url"
RECEIPT_NO_NOT_FOUND = "receipt no not found"
ORIGIN_ID_NOT_FOUND = "origin id not found"
retryable_messages = [RECEIPT_NO_NOT_FOUND]
MAX_RETRY_COUNT = 6


class Wasabi(SingularExportAgent):
    provider_slug = PROVIDER_SLUG

    config = Config(ConfigValue("base_url", key=BASE_URL_KEY, default="http://localhost"))

    def __init__(self):
        super().__init__()
        self.api_class = ActeolMockAPI if settings.DEBUG else ActeolAPI

        # Set up Prometheus metric types
        self.prometheus_metrics = {
            "counters": ["requests_sent", "failed_requests", "transactions"],
            "histograms": ["request_latency"],
        }

    def get_retry_datetime(
        self, retry_count: int, *, exception: t.Optional[Exception] = None
    ) -> t.Optional[pendulum.DateTime]:
        # TEMPORARY: remove when implementing signals
        if (
            isinstance(exception, RequestException)
            and self.get_response_result(exception.response) not in retryable_messages
        ):
            return None
        if retry_count == 0:
            # first retry in 20 minutes.
            return pendulum.now("UTC") + pendulum.duration(minutes=20)
        elif retry_count <= MAX_RETRY_COUNT:
            # second retry at 10 AM the next day.
            return self.next_available_retry_time(10)
        else:
            # after the previous seven tries, give up.
            return None

    @staticmethod
    def get_loyalty_identifier(export_transaction: models.ExportTransaction) -> str:
        return hashlib.sha1("Bink-Wasabi-" f"{export_transaction.decrypted_credentials['email']}".encode()).hexdigest()

    def make_export_data(self, export_transaction: models.ExportTransaction, session: db.Session) -> AgentExportData:
        return AgentExportData(
            outputs=[
                AgentExportDataOutput(
                    "export.json",
                    {
                        "origin_id": self.get_loyalty_identifier(export_transaction),
                        "ReceiptNo": export_transaction.transaction_id,
                    },
                )
            ],
            transactions=[export_transaction],
            extra_data={"credentials": export_transaction.decrypted_credentials},
        )

    def export(self, export_data: AgentExportData, *, retry_count: int = 0, session: db.Session):
        body: dict
        _, body = export_data.outputs[0]  # type: ignore
        api = self.api_class(self.config.get("base_url", session=session))
        request_timestamp = pendulum.now().to_datetime_string()
        endpoint = "/PostMatchedTransaction"
        response = api.post_matched_transaction(body, endpoint)
        response_timestamp = pendulum.now().to_datetime_string()

        request_url = api.base_url + endpoint
        atlas.queue_audit_message(
            atlas.make_audit_message(
                self.provider_slug,
                atlas.make_audit_transactions(
                    export_data.transactions, tx_loyalty_ident_callback=self.get_loyalty_identifier
                ),
                request=body,
                request_timestamp=request_timestamp,
                response=response,
                response_timestamp=response_timestamp,
                request_url=request_url,
                retry_count=retry_count,
            )
        )

        # raise exception for first 7 retries
        if msg := self.get_response_result(response):
            if msg == RECEIPT_NO_NOT_FOUND and retry_count <= MAX_RETRY_COUNT or msg == ORIGIN_ID_NOT_FOUND:
                # fail the export for it to be retried later
                raise RequestException(response=response)
            self.log.warn(f"Acteol API response contained message: {msg}")

    def get_response_result(self, response: Response) -> t.Optional[str]:
        if msg := response.json().get("Message"):
            return msg.lower()
        else:
            return None
