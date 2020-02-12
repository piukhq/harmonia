import json
from enum import Enum
from urllib.parse import urljoin

import settings
from app import models
from app.reporting import get_logger
from app.core.requests_retry import requests_retry_session


log = get_logger("atlas")


class Atlas:
    class Status(Enum):
        BINK_ASSIGNED = "BINK-ASSIGNED"
        MERCHANT_ASSIGNED = "MERCHANT-ASSIGNED"
        NOT_ASSIGNED = "NOT-ASSIGNED"

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.session = requests_retry_session()

    def post(self, endpoint: str, body: dict = None, *, name: str) -> dict:
        log.debug(f"Posting {name} request with parameters: {body}.")
        headers = {"Content-Type": "application/json", "Authorization": f"Token {settings.SERVICE_API_KEY}"}
        url = urljoin(self.base_url, endpoint)
        response = self.session.post(url, headers=headers, json=body)
        response.raise_for_status()
        return response.json()

    def save_transaction(
        self, provider_slug: str, response: str, transaction: models.MatchedTransaction, status: "Atlas.Status"
    ) -> dict:
        endpoint = f"{self.base_url}/transaction/save"
        body = {
            "scheme_provider": provider_slug,
            "response": json.dumps(response),
            "transaction_id": transaction.transaction_id,
            "status": status.value,
            "transaction_date": transaction.transaction_date.to_datetime_string(),
            "user_id": str(transaction.payment_transaction.user_identity.user_id),
            "amount": transaction.spend_amount,
        }
        return self.post(endpoint, body, name="save transaction")


atlas = Atlas(settings.ATLAS_URL)
