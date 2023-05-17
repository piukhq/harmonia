import uuid

import requests
from soteria.configuration import Configuration

import settings
from app.core.requests_retry import requests_retry_session
from app.reporting import get_logger

log = get_logger("the-works")


class TheWorksAPI:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.session = requests_retry_session()

    def post(self, body: dict = None, *, name: str) -> requests.models.Response:
        log.debug(f"Posting {name} request with parameters: {body}.")
        response = self.session.post(self.base_url, json=body)
        response.raise_for_status()
        return response

    def transactions(self, body: dict, endpoint: str) -> requests.models.Response:
        return self.post(endpoint, body, name="post_matched_transaction")

    def transaction_history(self, loyalty_id: str) -> dict:
        # build json rpc request to call transaction history endpoint
        history_transactions = self._history_request(loyalty_id)
        return history_transactions

    def _history_request(self, card_number: str):
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
                "POINTS",  # history type
            ],
        }
        return self.post(body, name="retrieve_transaction_history")

    def get_credentials(self) -> (str, str):
        config = Configuration(
            "the_works",
            Configuration.TRANSACTION_MATCHING,
            settings.VAULT_URL,
            None,
            settings.EUROPA_URL,
            settings.AAD_TENANT_ID,
        )
        user_id = config.security_credentials["outbound"]["credentials"][0]["value"]["user_id"]
        password = config.security_credentials["outbound"]["credentials"][0]["value"]["password"]
        return user_id, password
