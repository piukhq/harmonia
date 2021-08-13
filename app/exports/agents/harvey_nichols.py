import typing as t

import pendulum
from requests import RequestException, Response

import settings
from app import db, models
from app.config import KEY_PREFIX, Config, ConfigValue
from app.exports.agents import AgentExportData, AgentExportDataOutput, SingularExportAgent
from app.service import atlas
from app.service.harvey_nichols import HarveyNicholsAPI
from harness.exporters.harvey_nichols_mock import HarveyNicholsMockAPI

PROVIDER_SLUG = "harvey-nichols"
BASE_URL_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.base_url"

SUCCESS = "success"
ALREADY_ASSIGNED = "alreadyassigned"


class HarveyNichols(SingularExportAgent):
    provider_slug = PROVIDER_SLUG

    config = Config(ConfigValue("base_url", key=BASE_URL_KEY, default="https://localhost"))

    def __init__(self):
        super().__init__()
        self.api_class = HarveyNicholsMockAPI if settings.DEBUG is True else HarveyNicholsAPI

        # Set up Prometheus metric types
        self.prometheus_metrics = {
            "counters": ["failed_requests", "transactions"],
            "histograms": ["request_latency"],
        }

    @staticmethod
    def get_loyalty_identifier(matched_transaction: models.MatchedTransaction) -> str:
        return matched_transaction.payment_transaction.user_identity.decrypted_credentials["card_number"]

    def make_export_data(self, matched_transaction: models.MatchedTransaction) -> AgentExportData:
        user_identity = matched_transaction.payment_transaction.user_identity
        scheme_account_id = user_identity.scheme_account_id

        return AgentExportData(
            outputs=[
                AgentExportDataOutput(
                    "export.json",
                    {
                        "CustomerClaimTransactionRequest": {
                            "token": "token",
                            "customerNumber": self.get_loyalty_identifier(matched_transaction),
                            "id": matched_transaction.transaction_id,
                        }
                    },
                )
            ],
            transactions=[matched_transaction],
            extra_data={"credentials": user_identity.decrypted_credentials, "scheme_account_id": scheme_account_id},
        )

    def export(self, export_data: AgentExportData, *, retry_count: int = 0, session: db.Session):
        body: dict
        _, body = export_data.outputs[0]  # type: ignore
        api = self.api_class(self.config.get("base_url", session=session))
        request_timestamp = pendulum.now().to_datetime_string()
        response = api.claim_transaction(export_data.extra_data, body)
        response_timestamp = pendulum.now().to_datetime_string()

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
            )
        )
        if self.get_response_result(response) not in [SUCCESS, ALREADY_ASSIGNED]:
            raise RequestException(response=response)

    def get_response_result(self, response: Response) -> t.Optional[str]:
        return response.json()["CustomerClaimTransactionResponse"]["outcome"].lower()
