from pathlib import Path

import pendulum
import requests

import settings
from app import models
from app.core.requests_retry import requests_retry_session
from app.db import redis
from app.reporting import get_logger
from app.service import atlas
from app.utils import urljoin

log = get_logger("tgi-fridays")

TGIF_SECRET_KEY = "tgi-fridays-admin-key"
TOKEN_CACHE_TTL = 259198


class TGIFridaysAPI:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.session = requests_retry_session()

    @staticmethod
    def _read_secret(key: str) -> str:
        try:
            path = Path(settings.SECRETS_PATH) / key
            with path.open() as f:
                return f.read()
        except FileNotFoundError as e:
            log.exception(e)
            raise

    def _get_token(self) -> str:
        if token := redis.get(TGIF_SECRET_KEY):
            return token

        token = self._read_secret(TGIF_SECRET_KEY)
        redis.set(TGIF_SECRET_KEY, token)
        redis.expire(TGIF_SECRET_KEY, TOKEN_CACHE_TTL)

        return token

    def post(self, endpoint: str, body: dict | None = None, *, name: str) -> requests.models.Response:
        auth_token = f"Bearer {self._get_token()}"
        headers = {"Authorization": auth_token}
        log.debug(f"Posting {name} request with parameters: {body}.")
        url = urljoin(self.base_url, endpoint)
        response = self.session.post(url, json=body, headers=headers)
        return response

    def transactions(self, body: dict) -> requests.models.Response:
        return self.post("/api2/dashboard/users/support", body, name="post_matched_transaction")

    def transaction_history(self, transaction: models.ExportTransaction) -> list[dict]:
        # build request to call transaction history endpoint
        # send request and responses to atlas for audit
        request_timestamp = pendulum.now().to_datetime_string()
        endpoint = f"/api2/dashboard/users/extensive_timeline?user_id={transaction.loyalty_id}"
        auth_token = f"Bearer {self._get_token()}"
        headers = {"Authorization": auth_token}
        url = urljoin(self.base_url, endpoint)
        resp = self.session.get(url, headers=headers)

        response_timestamp = pendulum.now().to_datetime_string()
        message = atlas.make_audit_message(
            transaction.provider_slug,
            atlas.make_audit_transactions([transaction], tx_loyalty_ident_callback=lambda tx: tx.loyalty_id),
            request={"url": resp.url},
            request_timestamp=request_timestamp,
            response=resp,
            response_timestamp=response_timestamp,
            request_url=resp.url,
            retry_count=0,
        )

        atlas.queue_audit_message(message, destination="atlas")

        resp.raise_for_status()  # failures will be retried
        return resp.json()["checkins"]
