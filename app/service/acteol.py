from urllib.parse import urljoin

import requests

from app.reporting import get_logger
from app.core.requests_retry import requests_retry_session

log = get_logger("acteol")


class ActeolAPI:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.session = requests_retry_session()

    def post(self, endpoint: str, body: dict = None, *, name: str) -> requests.models.Response:
        log.debug(f"Posting {name} request with parameters: {body}.")
        url = urljoin(self.base_url, endpoint)
        response = self.session.post(url, json=body)
        response.raise_for_status()
        return response

    def post_matched_transaction(self, body: dict) -> requests.models.Response:
        endpoint = f"{self.base_url}/PostMatchedTransaction"
        return self.post(endpoint, body, name="post_matched_transaction")
