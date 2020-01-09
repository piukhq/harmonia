from urllib.parse import urljoin
from app.reporting import get_logger
from app.core.requests_retry import requests_retry_session


log = get_logger("harvey-nichols")


class HarveyNicholsAPI:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.session = requests_retry_session()

    def post(self, endpoint: str, body: dict = None, *, name: str) -> dict:
        log.debug(f"Posting {name} request with parameters: {body}.")
        url = urljoin(self.base_url, endpoint)
        response = self.session.post(url, json=body)
        response.raise_for_status()
        return response.json()

    def claim_transaction(self, token: str, card_number: str, transaction_id: str) -> dict:
        endpoint = f"{self.base_url}/WebCustomerLoyalty/services/CustomerLoyalty/ClaimTransaction"
        body = {
            "CustomerClaimTransactionRequest": {"token": token, "customerNumber": card_number, "id": transaction_id}
        }
        return self.post(endpoint, body, name="claim_transaction")["CustomerClaimTransactionResponse"]
