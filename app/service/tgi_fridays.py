import json
from pathlib import Path
from urllib.parse import urljoin

import requests

import settings
from app import models
from app.core.requests_retry import requests_retry_session
from app.db import redis
from app.reporting import get_logger

log = get_logger("tgi-fridays")

TGIF_SECRET_KEY = "tgi-fridays-outbound-key"
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
                return json.loads(f.read())
        except FileNotFoundError as e:
            log.exception(e)
            raise

    def _get_token(self) -> str:
        secret_key_name = "tgi-fridays-harmonia-oauth-key"

        if token := redis.get(secret_key_name):
            return token

        token = self._read_secret(TGIF_SECRET_KEY)
        redis.set(secret_key_name, token)
        redis.expire(secret_key_name, TOKEN_CACHE_TTL)

        return token

    def post(self, endpoint: str, body: dict = None, *, name: str) -> requests.models.Response:
        auth_token = f"Bearer {self._get_token()}"
        headers = {"Authorization": auth_token}
        log.debug(f"Posting {name} request with parameters: {body}.")
        url = urljoin(self.base_url, endpoint)
        response = self.session.post(url, json=body, headers=headers)
        response.raise_for_status()
        return response

    def transactions(self, body: dict, endpoint: str) -> requests.models.Response:
        return self.post(endpoint, body, name="post_matched_transaction")

    def transaction_history(self, transaction: models.ExportTransaction, provider_slug: str) -> dict:
        # build request to call transaction history endpoint
        # send request and responses to atlas for audit
        # request_timestamp = pendulum.now().to_datetime_string()
        endpoint = f"/api2/dashboard/users/extensive_timeline?user_id={transaction.loyalty_id}"
        client_id = "some_client_id"
        headers = {f"Authorization: Bearer {client_id}"}
        resp = self.session.get(urljoin(self.base_url, endpoint), headers=headers)

        # response_timestamp = pendulum.now().to_datetime_string()
        # message = atlas.make_audit_message(
        #     provider_slug,
        #     atlas.make_audit_transactions([transaction], tx_loyalty_ident_callback=lambda tx: tx.loyalty_id),
        #     request=sanitise_logs(request_body, provider_slug),
        #     request_timestamp=request_timestamp,
        #     response=response,
        #     response_timestamp=response_timestamp,
        #     request_url=response.url,
        #     retry_count=0,
        # )
        #
        # atlas.queue_audit_message(message, destination="atlas")
        return resp.json()["checkins"]
