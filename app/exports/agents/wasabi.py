import hashlib
import typing as t
from requests import Response, RequestException
import pendulum
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

    @staticmethod
    def get_loyalty_identifier(matched_transaction: models.MatchedTransaction) -> str:
        return hashlib.sha1(
            "Bink-Wasabi-"
            f"{matched_transaction.payment_transaction.user_identity.decrypted_credentials['email']}".encode()
        ).hexdigest()

    def make_export_data(self, matched_transaction: models.MatchedTransaction) -> AgentExportData:
        return AgentExportData(
            outputs=[
                AgentExportDataOutput(
                    "export.json",
                    {
                        "origin_id": self.get_loyalty_identifier(matched_transaction),
                        "ReceiptNo": matched_transaction.transaction_id,
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
        api = self.api_class(self.config.get("base_url", session=session))
        request_timestamp = pendulum.now().to_datetime_string()
        response = api.post_matched_transaction(body)
        response_timestamp = pendulum.now().to_datetime_string()

        if msg := response.json().get("Message"):
            if (
                msg.lower() == "receipt no not found" or msg.lower() == "origin id not found"
            ) and self.get_retry_datetime(retry_count):
                # fail the export for it to be retried later
                raise RequestException(response=response)

        self.log.warn(f"Acteol API response contained message: {msg}")

        audit_message = atlas.make_audit_message(
            self.provider_slug,
            atlas.make_audit_transactions(
                export_data.transactions, tx_loyalty_ident_callback=self.get_loyalty_identifier
            ),
            request=body,
            request_timestamp=request_timestamp,
            response=response,
            response_timestamp=response_timestamp,
        )
        return audit_message

    def get_response_result(self, response: Response) -> t.Optional[str]:
        return response.json().get("Message").lower()
