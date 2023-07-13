import uuid

import requests
from soteria.configuration import Configuration

import settings
from app.core.requests_retry import requests_retry_session
from app.reporting import get_logger

log = get_logger("the-works")


class TheWorksAPI:
    def __init__(self, base_url: str, failover_url: str) -> None:
        self.base_url = base_url
        self.failover_url = failover_url
        self.session = requests_retry_session()

    def post(self, body: dict = None, *, name: str) -> requests.models.Response:
        log.debug(f"Posting {name} request with parameters: {body}.")
        response = self.session.post(self.base_url, json=body)
        if not response.ok:
            user_id, password = self.get_credentials(failover=True)
            if body:
                body["params"][2] = user_id
                body["params"][3] = password
            response = self.session.post(self.failover_url, json=body)
        return response

    def transactions(self, body: dict, endpoint: str) -> requests.models.Response:
        return self.post(body, name="post_matched_transaction")

    def transaction_history(self, loyalty_id: str) -> dict:
        # build json rpc request to call transaction history endpoint
        history_transactions = self._history_request(loyalty_id)
        return history_transactions

    def _history_request(self, card_number: str) -> dict:
        transaction_code = str(uuid.uuid4())
        user_id, password = self.get_credentials()
        body = {
            "jsonrpc": "2.0",
            "method": "dc_995",  # request method
            "id": 1,
            "params": [
                "en",  # language code
                transaction_code,
                user_id,
                password,
                card_number,  # givex number
                "",  # Serial number
                "",  # card iso
                "Points",  # history type
            ],
        }
        return self.post(body, name="retrieve_transaction_history").json()

    def get_credentials(self, failover: bool = False) -> tuple[str, str]:
        config = Configuration(
            "the-works-failover" if failover else "the-works",
            Configuration.TRANSACTION_MATCHING,
            settings.VAULT_URL,
            None,
            settings.EUROPA_URL,
            settings.AAD_TENANT_ID,
        )
        user_id = config.security_credentials["outbound"]["credentials"][0]["value"]["user_id"]
        password = config.security_credentials["outbound"]["credentials"][0]["value"]["password"]
        return user_id, password
