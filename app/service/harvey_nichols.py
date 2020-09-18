import requests
import settings

from urllib.parse import urljoin
from app.reporting import get_logger
from app.core.requests_retry import requests_retry_session
from user_auth_token.core import UserTokenStore

log = get_logger("harvey-nichols")


class HarveyNicholsAPI:
    token_store = UserTokenStore(settings.REDIS_URL)

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.session = requests_retry_session()

    def post(self, endpoint: str, body: dict = None, *, name: str) -> requests.Response:
        log.debug(f"Posting {name} request with parameters: {body}.")
        url = urljoin(self.base_url, endpoint)
        response = self.session.post(url, json=body)
        response.raise_for_status()
        # Save the request and response for billing and audit
        return response

    def claim_transaction(self, extra_data: dict, body: dict) -> requests.Response:
        credentials = extra_data["credentials"]
        scheme_account_id = extra_data["scheme_account_id"]

        token = self.get_token(credentials, scheme_account_id)
        endpoint = f"{self.base_url}/WebCustomerLoyalty/services/CustomerLoyalty/ClaimTransaction"
        body["CustomerClaimTransactionRequest"]["token"] = token

        response = self.post(endpoint, body, name="claim_transaction")

        if "AuthFailed" in response.text:
            token = self.get_new_token(credentials, scheme_account_id)
            body["CustomerClaimTransactionRequest"]["token"] = token
            response = self.post(endpoint, body, name="claim_transaction")

        return response

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
