import requests
import settings
from soteria.configuration import Configuration
from app.reporting import get_logger
from app.core.requests_retry import requests_retry_session

log = get_logger("bpl")


class BplAPI():
    def __init__(self, base_url: str, scheme_slug: str) -> None:
        self.base_url = base_url
        self.scheme_slug = scheme_slug
        self.session = requests_retry_session()

    def post(self, endpoint: str, body: dict = None, *, name: str) -> requests.models.Response:
        log.debug(f"Posting {name} request with parameters: {body}.")
        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Token {self.get_security_token()}"}
        response = self.session.post(url, headers=headers, json=body)
        response.raise_for_status()
        return response

    def post_matched_transaction(self, body: dict) -> requests.models.Response:
        endpoint = "/trenette/transaction"
        return self.post(endpoint, body, name="post_matched_transaction")

    def get_security_token(self):
        handler = Configuration.TRANSACTION_MATCHING
        conf = Configuration(self.scheme_slug, handler, settings.VAULT_URL, None, settings.EUROPA_URL)
        return conf.security_credentials["outbound"]["credentials"][0]["value"]["token"]
