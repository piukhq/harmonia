import settings
from app import db, models
from app.config import KEY_PREFIX, ConfigValue
from app.encryption import decrypt_credentials
from app.exports.agents import AgentExportData, AgentExportDataOutput, SingularExportAgent
from app.failed_transaction import FailedTransaction
from app.service.atlas import Atlas, atlas
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

    def internal_requests(
        self, response: dict, transaction: models.MatchedTransaction, matched_transaction_id: int
    ) -> None:
        response_outcome = response["outcome"].lower()
        if response_outcome == "success":
            atlas.save_transaction(self.provider_slug, response, transaction, Atlas.Status.BINK_ASSIGNED)
        elif response_outcome in ["alreadyclaimed", "alreadyassigned"]:
            atlas.save_transaction(self.provider_slug, response, transaction, Atlas.Status.MERCHANT_ASSIGNED)
            self.log.debug(f"Matched transaction {matched_transaction_id} is already assigned to a customer.")
        else:
            limit_reached = FailedTransaction(max_retries=5).retry(self.provider_slug, matched_transaction_id)
            if limit_reached:
                atlas.save_transaction(self.provider_slug, response, transaction, Atlas.Status.NOT_ASSIGNED)
                self.log.debug(f"Matched transaction {matched_transaction_id} was not assigned.")

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

        response = self.api.claim_transaction(export_data.extra_data, body)

        atlas.save_transaction(self.provider_slug, response, body, export_data.transactions)
