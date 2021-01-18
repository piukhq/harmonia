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


class AuditTransaction(t.TypedDict):
    transaction_id: str
    user_id: str
    spend_amount: int
    transaction_date: str
    merchant_identifier: str


class AuditData(t.TypedDict, total=False):
    request: t.Optional[t.Dict[str, t.Any]]
    response: t.Optional[t.Dict[str, t.Any]]
    file_names: t.Optional[t.List[str]]


class AtlasPayload(t.TypedDict):
    scheme_provider: str
    transactions: t.List[AuditTransaction]
    audit_data: AuditData


class Atlas:
    class Status(Enum):
        BINK_ASSIGNED = "BINK-ASSIGNED"
        MERCHANT_ASSIGNED = "MERCHANT-ASSIGNED"
        NOT_ASSIGNED = "NOT-ASSIGNED"

    def __init__(self) -> None:
        self.session = requests_retry_session()

    @staticmethod
    def make_audit_transactions(
        transactions: t.List[models.MatchedTransaction],
        *,
        tx_merchant_ident_callback: t.Callable[[models.MatchedTransaction], str],
        tx_record_uid_callback: t.Optional[t.Callable[[models.MatchedTransaction], t.Optional[str]]] = None,
    ):
        return [
            AuditTransaction(
                transaction_id=tx.id,
                user_id=tx.payment_transaction.user_identity.user_id,
                spend_amount=tx.spend_amount,
                transaction_date=pendulum.instance(tx.transaction_date).to_datetime_string(),
                merchant_identifier=tx_merchant_ident_fn(tx),
            )
            for tx in transactions
        ]

    def save_transactions(
        self,
        provider_slug: str,
        transactions: t.List[AuditTransaction],
        *,
        request: t.Optional[dict] = None,
        request_timestamp: t.Optional[str] = None,
        response: t.Optional[requests.Response] = None,
        response_timestamp: t.Optional[str] = None,
        blob_names: t.Optional[t.List[str]] = None,
    ):
        audit_data = AuditData()
        if request is not None:
            audit_data["request"] = {"body": request, "timestamp": request_timestamp}

        if response is not None:
            try:
                body = response.json()
            except ValueError:
                body = response.content
            audit_data["response"] = {
                "body": body,
                "status_code": response.status_code,
                "timestamp": response_timestamp,
            }
        if blob_names:
            audit_data["file_names"] = blob_names

        payload = AtlasPayload(scheme_provider=provider_slug, transactions=transactions, audit_data=audit_data)
        if settings.SIMULATE_EXPORTS:
            log.warning(f"Not saving {provider_slug} transaction(s) because SIMULATE_EXPORTS is enabled.")
            log.debug(f"Simulated audit request with payload:\n{payload}")
        else:
            queue.add(payload, provider=provider_slug, queue_name="tx_matching")


atlas = Atlas()
