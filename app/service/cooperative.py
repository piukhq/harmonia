import settings
import requests

from app.reporting import get_logger
from soteria.configuration import Configuration
from app.core.requests_retry import requests_retry_session


provider_slug = "cooperative"
log = get_logger(provider_slug)

config = Configuration(
    provider_slug,
    Configuration.TRANSACTION_MATCHING_HANDLER,
    settings.VAULT_URL,
    settings.VAULT_TOKEN,
    settings.CONFIG_SERVICE_URL,
)


class Cooperative:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.session = requests_retry_session()

    def post(self, request_data: dict, *, name: str) -> requests.models.Response:
        log.debug(f"Posting {name} request with parameters: {request_data['json']}.")
        response = self.session.post(self.base_url, **request_data)
        response.raise_for_status()
        return response

    def merchant_request(self, request_data) -> requests.models.Response:
        return self.post(request_data, name="Cooperative merchant request")


cooperative = Cooperative(config.merchant_url)
