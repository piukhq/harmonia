import json
import os
from pathlib import Path
from urllib.parse import urlencode, urljoin

import arrow
import requests
from user_auth_token import UserTokenStore

import settings
from app.core.requests_retry import requests_retry_session
from app.reporting import get_logger

log = get_logger("itsu")

ITSU_SECRET_KEY = "itsu-outbound-compound-key-join"
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ItsuApi:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.session = requests_retry_session()
        self.oauth_token_timeout = 75600  # n_seconds in 21 hours
        self.token_store = UserTokenStore(settings.REDIS_URL)
        self.scheme_slug = "itsu"

    @staticmethod
    def _read_secret(key: str) -> str:
        try:
            root_path = Path(ROOT_DIR).parents[0]
            path = Path(os.path.join(root_path, "mnt/secrets")) / key
            with path.open() as f:
                return json.loads(f.read())
        except FileNotFoundError as e:
            log.exception(e)
            raise

    def _store_token(self, token: str, current_timestamp: int) -> None:
        token_dict = {
            f"{self.scheme_slug.replace('-', '_')}_access_token": token,
            "timestamp": current_timestamp,
        }
        self.token_store.set(scheme_account_id=self.scheme_slug, token=json.dumps(token_dict))

    def _refresh_token(self) -> str:
        credentials = self._read_secret(ITSU_SECRET_KEY)
        url = urljoin(self.base_url, "token")
        payload = {"username": credentials["username"], "password": credentials["password"], "grant_type": "password"}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        url_encoded_payload = urlencode(payload)
        response = self.session.post(url, data=url_encoded_payload, headers=headers)
        response.raise_for_status()

        return response.json()["access_token"]

    def _token_is_valid(self, token: dict, current_timestamp: int) -> bool:
        if isinstance(token["timestamp"], list):
            token_timestamp = token["timestamp"][0]
        else:
            token_timestamp = token["timestamp"]

        return current_timestamp - token_timestamp < self.oauth_token_timeout

    def get_token(self):
        have_valid_token = False
        current_timestamp = arrow.utcnow().int_timestamp
        token = ""
        try:
            cached_token = json.loads(self.token_store.get(self.scheme_slug))
            try:
                if self._token_is_valid(cached_token, current_timestamp):
                    have_valid_token = True
                    token = cached_token[f"{self.scheme_slug.replace('-', '_')}_access_token"]
            except (KeyError, TypeError) as e:
                log.exception(e)
        except (KeyError, self.token_store.NoSuchToken):
            pass

        if not have_valid_token:
            token = self._refresh_token()
            self._store_token(token, current_timestamp)

        return f"Bearer {token}"

    def post(self, endpoint: str, body: dict = None, *, name: str) -> requests.models.Response:
        auth_token = self.get_token()
        headers = {"Authorization": auth_token}
        log.debug(f"Posting {name} request with parameters: {body}.")
        url = f"{self.base_url}{endpoint}"
        response = self.session.post(url, json=body, headers=headers)
        response.raise_for_status()
        return response

    def post_matched_transaction(self, body: dict, endpoint: str) -> requests.models.Response:
        return self.post(endpoint, body, name="post_matched_transaction")
