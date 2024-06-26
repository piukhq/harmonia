import requests

from app.core.requests_retry import requests_retry_session
from app.reporting import get_logger

log = get_logger("costa")


class CostaAPI:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.session = requests_retry_session()

    def post(self, endpoint: str, body: dict = None, *, name: str) -> requests.models.Response:
        log.debug(f"Posting {name} request with parameters: {body}.")
        url = f"{self.base_url}{endpoint}"
        response = self.session.post(url, json=body)
        response.raise_for_status()
        return response

    def transactions(self, body: dict, endpoint: str) -> requests.models.Response:
        return self.post(endpoint, body, name="post_matched_transaction")
