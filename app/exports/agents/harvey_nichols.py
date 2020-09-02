import settings
import pendulum

from app import db, models
from app.config import KEY_PREFIX, ConfigValue
from app.encryption import decrypt_credentials
from app.exports.agents import AgentExportData, AgentExportDataOutput, SingularExportAgent
from app.service.atlas import atlas
from app.service.harvey_nichols import HarveyNicholsAPI
from harness.exporters.harvey_nichols_mock import HarveyNicholsMockAPI

PROVIDER_SLUG = "harvey-nichols"
BASE_URL_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.base_url"


class HarveyNichols(SingularExportAgent):
    provider_slug = PROVIDER_SLUG

    class Config:
        base_url = ConfigValue(BASE_URL_KEY, "https://localhost")

    def __init__(self):
        super().__init__()
        if settings.DEVELOPMENT is True:
            # Use mocked HN endpoints
            self.api = HarveyNicholsMockAPI(self.Config.base_url)
        else:
            self.api = HarveyNicholsAPI(self.Config.base_url)

    def make_export_data(self, matched_transaction: models.MatchedTransaction) -> AgentExportData:
        user_identity = matched_transaction.payment_transaction.user_identity
        credentials = decrypt_credentials(user_identity.credentials)
        scheme_account_id = user_identity.scheme_account_id

        return AgentExportData(
            outputs=[
                AgentExportDataOutput(
                    "export.json",
                    {
                        "CustomerClaimTransactionRequest": {
                            "token": "token",
                            "customerNumber": credentials["card_number"],
                            "id": matched_transaction.transaction_id,
                        }
                    },
                )
            ],
            transactions=[matched_transaction],
            extra_data={"credentials": credentials, "scheme_account_id": scheme_account_id},
        )

    def export(self, export_data: AgentExportData, *, session: db.Session):
        _, body = export_data.outputs[0]
        request_timestamp = pendulum.now().to_datetime_string()
        response = self.api.claim_transaction(export_data.extra_data, body)
        response_timestamp = pendulum.now().to_datetime_string()

        atlas.save_transaction(
            self.provider_slug, response, body, export_data.transactions, request_timestamp, response_timestamp
        )
