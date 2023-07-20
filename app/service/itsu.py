import functools
import json
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode, urljoin

import requests
from user_auth_token import UserTokenStore

import settings
from app.core.requests_retry import requests_retry_session
from app.reporting import get_logger

log = get_logger("itsu")

ITSU_SECRET_KEY = "itsu-outbound-compound-key-join"
TOKEN_CACHE_TTL = 259199
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ttl_cache(func):
    cache = {}

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = (args, frozenset(kwargs.items()))

        if key in cache:
            result, timestamp = cache[key]
            current_time = datetime.now()

            if current_time - timestamp < TOKEN_CACHE_TTL:
                return result
            else:
                del cache[key]

        result = func(*args, **kwargs)
        cache[key] = (result, datetime.now())
        return result

    return wrapper


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

    @ttl_cache
    def _get_token(self) -> str:
        credentials = self._read_secret(ITSU_SECRET_KEY)
        url = urljoin(self.base_url, "token")
        payload = {
            "username": credentials["username"],  # type:ignore
            "password": credentials["password"],  # type:ignore
            "grant_type": "password",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        url_encoded_payload = urlencode(payload)
        response = self.session.post(url, data=url_encoded_payload, headers=headers)
        response.raise_for_status()

        return response.json()["access_token"]

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
