import json
import settings
import pendulum
import requests

from enum import Enum

from app import models
from app.reporting import get_logger
from app.core.requests_retry import requests_retry_session
from app.service import queue

log = get_logger("atlas")


class Atlas:
    class Status(Enum):
        BINK_ASSIGNED = "BINK-ASSIGNED"
        MERCHANT_ASSIGNED = "MERCHANT-ASSIGNED"
        NOT_ASSIGNED = "NOT-ASSIGNED"

    def __init__(self) -> None:
        self.session = requests_retry_session()

    def save_transaction(
            self, provider_slug: str,
            response: requests.Response,
            request: dict,
            transactions: list):

        if settings.SIMULATE_EXPORTS:
            log.warning(f"Not saving {provider_slug} transaction because SIMULATE_EXPORTS is enabled.")
            log.debug(f'Simulated request: {transactions} with response: "{response}" ')
            return {}

        body = {
            "scheme_provider": provider_slug,
            "response": response.json(),
            "request": request,
            "status_code": response.status_code,
            "timestamp": pendulum.now()
        }

        queue.add(body, provider=provider_slug, queue_name="tx_matching")
        # return self.post(endpoint, body, name="save transaction")


atlas = Atlas()
