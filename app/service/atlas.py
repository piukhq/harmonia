import settings
import pendulum
import requests
import typing as t

from enum import Enum

from app.reporting import get_logger
from app.core.requests_retry import requests_retry_session
from app import models
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
        self,
        provider_slug: str,
        response: requests.Response,
        request: dict,
        transactions: t.List[models.MatchedTransaction],
        request_timestamp,
        response_timestamp,
    ):

        if settings.SIMULATE_EXPORTS:
            log.warning(f"Not saving {provider_slug} transaction because SIMULATE_EXPORTS is enabled.")
            log.debug(f'Simulated request: {transactions} with response: "{response}" ')
            return {}

        transaction_sub_set = []
        for transaction in transactions:
            data = {
                "transaction_id": transaction.transaction_id,
                "user_id": transaction.payment_transaction.user_identity.user_id,
                "spend_amount": transaction.spend_amount,
                "transaction_date": pendulum.instance(transaction.transaction_date).to_datetime_string(),
            }
            transaction_sub_set.append(data)

        body = {
            "scheme_provider": provider_slug,
            "response": response.json(),
            "request": request,
            "status_code": response.status_code,
            "request_timestamp": request_timestamp,
            "response_timestamp": response_timestamp,
            "transactions": transaction_sub_set,
        }

        queue.add(body, provider=provider_slug, queue_name="tx_matching")


atlas = Atlas()
