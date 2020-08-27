import hashlib

from app import db, models
from app.config import KEY_PREFIX, ConfigValue
from app.encryption import decrypt_credentials
from app.exports.agents.bases.base import AgentExportData, AgentExportDataOutput
from app.exports.agents.bases.singular_export_agent import SingularExportAgent
from app.failed_transaction import FailedTransaction
from app.service.acteol import ActeolAPI
from app.service.atlas import Atlas, atlas

PROVIDER_SLUG = "wasabi-club"

BASE_URL_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.base_url"


class Wasabi(SingularExportAgent):
    provider_slug = PROVIDER_SLUG

    class Config:
        base_url = ConfigValue(BASE_URL_KEY, "http://localhost")

    def __init__(self):
        super().__init__()
        self.api = ActeolAPI(self.Config.base_url)

    def internal_requests(
        self, response: dict, transaction: models.MatchedTransaction, matched_transaction_id: int
    ) -> None:
        response_outcome = response["Message"].lower()
        if response_outcome == "stamp awarded":
            atlas.save_transaction(self.provider_slug, response, transaction, Atlas.Status.BINK_ASSIGNED)
        elif response_outcome == "stamp already earned":
            atlas.save_transaction(self.provider_slug, response, transaction, Atlas.Status.MERCHANT_ASSIGNED)
            self.log.debug(f"Stamp for matched transaction {matched_transaction_id} has already been earned.")
        elif response_outcome in ["origin id not found", "earn threshold not met"]:
            if response_outcome == "origin id not found":
                self.log.warn(f"Wasabi matched transaction export failed: {response_outcome}")
            atlas.save_transaction(self.provider_slug, response, transaction, Atlas.Status.NOT_ASSIGNED)
        else:
            limit_reached = FailedTransaction(max_retries=5).retry(self.provider_slug, matched_transaction_id)
            if limit_reached:
                atlas.save_transaction(self.provider_slug, response, transaction, Atlas.Status.NOT_ASSIGNED)
                self.log.debug(f"Matched transaction {matched_transaction_id} was not assigned.")

    def make_export_data(self, matched_transaction: models.MatchedTransaction) -> AgentExportData:
        user_identity = matched_transaction.payment_transaction.user_identity
        credentials = decrypt_credentials(user_identity.credentials)
        return AgentExportData(
            outputs=[
                AgentExportDataOutput(
                    "export.json",
                    {
                        "origin_id": hashlib.sha1(f'Bink-Wasabi-{credentials["email"]}'.encode()).hexdigest(),
                        "ReceiptNo": matched_transaction.transaction_id,
                    },
                )
            ],
            transactions=[matched_transaction],
            extra_data={"credentials": credentials},
        )

    def export(self, export_data: AgentExportData, *, session: db.Session):
        _, body = export_data.outputs[0]
        transaction = export_data.transactions[0]
        response = self.api.post_matched_transaction(body).json()
        if err := response.get("Error"):
            self.log.warn(f"Acteol API response contained 'Error': {err}")
        self.internal_requests(response, transaction, transaction.id)
