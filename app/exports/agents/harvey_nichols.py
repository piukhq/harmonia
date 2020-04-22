from user_auth_token.core import UserTokenStore

import settings
from app import db, models
from app.config import KEY_PREFIX, ConfigValue
from app.encryption import decrypt_credentials
from app.exports.agents import AgentExportData, AgentExportDataOutput, SingularExportAgent
from app.failed_transaction import FailedTransaction
from app.service.atlas import Atlas, atlas
from app.service.harvey_nichols import HarveyNicholsAPI

PROVIDER_SLUG = "harvey-nichols"
BASE_URL_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.base_url"


class HarveyNichols(SingularExportAgent):
    provider_slug = PROVIDER_SLUG
    token_store = UserTokenStore(settings.REDIS_URL)

    class Config:
        base_url = ConfigValue(BASE_URL_KEY, "https://localhost")

    def __init__(self):
        super().__init__()
        self.api = HarveyNicholsAPI(self.Config.base_url)

    def get_new_token(self, credentials, scheme_account_id):
        url = f"{self.Config.base_url}/WebCustomerLoyalty/services/CustomerLoyalty/SignOn"
        token_path = ["CustomerSignOnResult", "token"]
        credentials_json = {
            "CustomerSignOnRequest": {
                "username": credentials["email"],
                "password": credentials["password"],
                "applicationId": "CX_MOB",
                "deviceId": "",
            }
        }
        try:
            token = self.token_store.get_new(url, token_path, scheme_account_id, json=credentials_json)
        except UserTokenStore.TokenError:
            token = ""
        self.log.debug(f"New token has been assigned: {token}")

        return token

    def get_token(self, credentials, scheme_account_id):
        try:
            token = self.token_store.get(scheme_account_id)
        except UserTokenStore.NoSuchToken:
            token = self.get_new_token(credentials, scheme_account_id)
        return token

    def internal_requests(
        self, response: dict, transaction: models.MatchedTransaction, audit_data: dict, matched_transaction_id: int
    ) -> None:
        response_outcome = response["outcome"].lower()
        if response_outcome == "success":
            atlas.save_transaction(self.provider_slug, response, transaction, Atlas.Status.BINK_ASSIGNED)
        elif response_outcome in ["alreadyclaimed", "alreadyassigned"]:
            atlas.save_transaction(self.provider_slug, response, transaction, Atlas.Status.MERCHANT_ASSIGNED)
            self.log.debug(f"Matched transaction {matched_transaction_id} is already assigned to a different customer.")
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
        _, body = export_data.outputs.pop()
        transaction = export_data.transactions[0]
        credentials = export_data.extra_data["credentials"]
        scheme_account_id = export_data.extra_data["scheme_account_id"]

        token = self.get_token(credentials, scheme_account_id)
        response = self.api.claim_transaction(token, body)
        if response["outcome"] == "AuthFailed":
            token = self.get_new_token(credentials, scheme_account_id)
            response = self.api.claim_transaction(token, body)

        audit_data = {
            "token": token,
            "card_number": credentials["card_number"],
            "transaction_id": transaction.transaction_id,
        }
        self.internal_requests(response, transaction, audit_data, transaction.id)
