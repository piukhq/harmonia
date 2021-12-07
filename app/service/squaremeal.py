from requests import Response

from app.core.requests_retry import requests_retry_session
from app.reporting import get_logger

log = get_logger("squaremeal-api")


class SquareMeal:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.session = requests_retry_session()

    def post(self, endpoint: str, body: dict = None, *, name: str) -> Response:
        log.debug(f"Posting {name} request with parameters: {body}.")
        url = f"{self.base_url}{endpoint}"
        response = self.session.post(url, json=body)
        log.debug(f"Response to {name} request: {response.status_code} {response.reason}")
        response.raise_for_status()
        return response

    def transactions(self, body: dict) -> Response:
        endpoint = "/api/BinkTransactions"
        return self.post(endpoint, body, name="transactions")
