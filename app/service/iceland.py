import requests

from app.core.requests_retry import requests_retry_session
from app.reporting import get_logger

provider_slug = "iceland-bonus-card"
log = get_logger(provider_slug)


class IcelandAPI:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.session = requests_retry_session()

    def post(self, request_data: dict, *, name: str) -> requests.models.Response:
        log.debug(f"Posting {name} request with parameters: {request_data['json']}.")
        response = self.session.post(self.base_url, **request_data)
        response.raise_for_status()
        return response

    def merchant_request(self, request_data) -> requests.models.Response:
        return self.post(request_data, name="Iceland merchant")
