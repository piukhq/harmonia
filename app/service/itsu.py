import json
from pathlib import Path
from urllib.parse import urlencode, urljoin

import requests

import settings
from app.core.requests_retry import requests_retry_session
from app.db import redis
from app.reporting import get_logger

log = get_logger("itsu")

ITSU_SECRET_KEY = "itsu-outbound-compound-key-join"
TOKEN_CACHE_TTL = 259198


class ItsuApi:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.session = requests_retry_session()
        self.scheme_slug = "itsu"

    @staticmethod
    def _read_secret(key: str) -> str:
        try:
            path = Path(settings.SECRETS_PATH) / key
            with path.open() as f:
                return json.loads(f.read())
        except FileNotFoundError as e:
            log.exception(e)
            raise

    def _get_token(self) -> str:
        secret_key_name = f"{self.scheme_slug}-harmonia-oauth-key"
        if redis.exists(secret_key_name):
            return redis.get(secret_key_name).decode("utf-8")
        credentials = self._read_secret(ITSU_SECRET_KEY)
        url = urljoin(self.base_url, "token")
        payload = {
            "username": credentials["data"]["username"],  # type:ignore
            "password": credentials["data"]["password"],  # type:ignore
            "grant_type": "password",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        url_encoded_payload = urlencode(payload)
        response = self.session.post(url, data=url_encoded_payload, headers=headers)
        response.raise_for_status()
        token = response.json()["access_token"]
        redis.set(secret_key_name, token)
        redis.expire(secret_key_name, TOKEN_CACHE_TTL)
        return token

    def post(self, endpoint: str, body: dict = None, *, name: str) -> requests.models.Response:
        auth_token = f"Bearer {self._get_token()}"
        headers = {"Authorization": auth_token}
        log.debug(f"Posting {name} request with parameters: {body}.")
        url = f"{self.base_url}{endpoint}"
        response = self.session.post(url, json=body, headers=headers)
        response.raise_for_status()
        return response

    def post_matched_transaction(self, body: dict, endpoint: str) -> requests.models.Response:
        return self.post(endpoint, body, name="post_matched_transaction")
