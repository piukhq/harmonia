import hashlib
import json

import requests

from app.core.requests_retry import requests_retry_session
from app.reporting import get_logger

log = get_logger("slim-chickens")


class SlimChickensApi:
    def __init__(self, base_url: str, client_secret: str, client_id: str, auth_header: str) -> None:
        self.base_url = base_url
        self.session = requests_retry_session()
        self.scheme_slug = "slim-chickens"
        self.client_secret = client_secret
        self.client_id = client_id
        self.auth_header = auth_header

    @staticmethod
    def _generate_auth_hash(endpoint: str, payload: dict, secret: str):
        input_string = endpoint + json.dumps(payload) + secret
        return hashlib.sha256(input_string.encode()).hexdigest()

    def post(self, endpoint: str, body: dict = None, *, name: str) -> requests.models.Response:
        auth_hash = self._generate_auth_hash(endpoint, body, self.client_secret)
        headers = {
            "X-EES-AUTH-CLIENT-ID": self.client_id,
            "X-EES-AUTH-HASH": auth_hash,
        }
        log.debug(f"Posting {name} request with parameters: {body}.")
        url = f"{self.base_url}{endpoint}"
        response = self.session.post(url, json=body, headers=headers)
        response.raise_for_status()
        return response

    def post_matched_transaction(self, body: dict, endpoint: str) -> requests.models.Response:
        return self.post(endpoint, body, name="post_matched_transaction")
