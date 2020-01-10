import settings
import requests

from app.reporting import get_logger
from soteria.configuration import Configuration
from app.core.requests_retry import requests_retry_session


provider_slug = "iceland-bonus-card"
log = get_logger(provider_slug)

# TODO(cl): might be better to have the agent create this & the service instance
# TODO(cl): fix the bug in soteria that requires this horrible None handling
config = Configuration(
    provider_slug,
    Configuration.TRANSACTION_MATCHING_HANDLER,
    settings.VAULT_URL,
    settings.VAULT_TOKEN,
    settings.SOTERIA_URL if settings.SOTERIA_URL else 'http://localhost',
)


class Iceland:
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


iceland = Iceland(config.merchant_url)
