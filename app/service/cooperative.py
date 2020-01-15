import requests

from app.reporting import get_logger
from app.core.requests_retry import requests_retry_session


provider_slug = "cooperative"
log = get_logger(provider_slug)


class CooperativeAPI:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.session = requests_retry_session()

    def post(self, body: dict, *, name: str, headers: dict = None) -> requests.models.Response:
        log.debug(f"Posting {name} request with parameters: {body}.")
        response = self.session.post(self.base_url, json=body, headers=headers)
        response.raise_for_status()
        return response

    def export_transactions(self, body: dict, headers: dict) -> requests.models.Response:
        return self.post(body, headers=headers, name="co-op transaction export")
