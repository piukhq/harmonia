import json

from user_auth_token.core import UserTokenStore

from app import models
from app.db import session, run_query
from app.service.atlas import Atlas, atlas
from app.encryption import AESCipher
from app.failed_transaction import FailedTransaction
from app.service.harvey_nichols import HarveyNicholsAPI
from app.exports.agents.bases.single_export_agent import SingleExportAgent
from app.config import KEY_PREFIX, ConfigValue
import settings


PROVIDER_SLUG = "harvey-nichols"
BASE_URL_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.base_url"


class HarveyNichols(SingleExportAgent):
    provider_slug = PROVIDER_SLUG
    token_store = UserTokenStore(settings.REDIS_URL)

    class Config:
        base_url = ConfigValue(BASE_URL_KEY, "https://localhost")

    def __init__(self):
        super().__init__()
        self.api = HarveyNicholsAPI(self.Config.base_url)

    @staticmethod
    def decrypt_credentials(credentials: str) -> dict:
        aes = AESCipher(settings.AES_KEY.encode())
        return json.loads(aes.decrypt(credentials.replace(" ", "+")))

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

    def save_data(self, matched_transaction: models.MatchedTransaction, audit_data: dict) -> None:
        def export_transaction():
            session.add(
                models.ExportTransaction(
                    matched_transaction_id=matched_transaction.id,
                    transaction_id=matched_transaction.transaction_id,
                    provider_slug=self.provider_slug,
                    destination="",
                    data=audit_data,
                )
            )
            matched_transaction.status = models.MatchedTransactionStatus.EXPORTED
            session.commit()

        run_query(export_transaction)
        self.log.debug(f"The status of the transaction has been changed to: {matched_transaction.status}")

    def internal_requests(
        self, response: dict, transaction: models.MatchedTransaction, audit_data: dict, matched_transaction_id: int
    ) -> None:
        response_outcome = response["outcome"].lower()
        if response_outcome == "success":
            atlas.save_transaction(self.provider_slug, response, transaction, Atlas.Status.BINK_ASSIGNED)
            self.save_data(transaction, audit_data)
        elif response_outcome in ["alreadyclaimed", "alreadyassigned"]:
            atlas.save_transaction(self.provider_slug, response, transaction, Atlas.Status.MERCHANT_ASSIGNED)
            self.log.debug(f"Matched transaction {matched_transaction_id} is already assigned to a different customer.")
        else:
            limit_reached = FailedTransaction(settings.REDIS_URL, max_retries=5).retry(
                self.provider_slug, matched_transaction_id
            )
            if limit_reached:
                atlas.save_transaction(self.provider_slug, response, transaction, Atlas.Status.NOT_ASSIGNED)
                self.log.debug(f"Matched transaction {matched_transaction_id} was not assigned.")

    def export(self, matched_transaction_id: int) -> bool:
        transaction = run_query(lambda: session.query(models.MatchedTransaction).get(matched_transaction_id))
        credentials = self.decrypt_credentials(transaction.user_identity.credentials)
        scheme_account_id = transaction.user_identity.scheme_account_id
        token = self.get_token(credentials, scheme_account_id)

        response = self.api.claim_transaction(token, credentials["card_number"], transaction.transaction_id)
        if response["outcome"] == "AuthFailed":
            token = self.get_new_token(credentials, scheme_account_id)
            response = self.api.claim_transaction(token, credentials["card_number"], transaction.transaction_id)

        audit_data = {
            "token": token,
            "card_number": credentials["card_number"],
            "transaction_id": transaction.transaction_id,
        }
        self.internal_requests(response, transaction, audit_data, matched_transaction_id)

        return True
