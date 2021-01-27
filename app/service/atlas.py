import settings
import pendulum
import requests
import typing as t


from app.reporting import get_logger
from app import models
from app.service import queue

log = get_logger("atlas")


class AuditTransaction(t.TypedDict):
    transaction_id: str
    user_id: str
    spend_amount: int
    transaction_date: str
    loyalty_identifier: str
    record_uid: t.Optional[str]


class AuditData(t.TypedDict, total=False):
    request: t.Optional[t.Dict[str, t.Any]]
    response: t.Optional[t.Dict[str, t.Any]]
    file_names: t.Optional[t.List[str]]


class MessagePayload(t.TypedDict):
    provider_slug: str
    transactions: t.List[AuditTransaction]
    audit_data: AuditData


def make_audit_transactions(
    transactions: t.List[models.MatchedTransaction],
    *,
    tx_loyalty_ident_callback: t.Callable[[models.MatchedTransaction], str],
    tx_record_uid_callback: t.Optional[t.Callable[[models.MatchedTransaction], t.Optional[str]]] = None,
) -> t.List[AuditTransaction]:
    return [
        AuditTransaction(
            transaction_id=tx.transaction_id,
            user_id=tx.payment_transaction.user_identity.user_id,
            spend_amount=tx.spend_amount,
            transaction_date=pendulum.instance(tx.transaction_date).to_datetime_string(),
            loyalty_identifier=tx_loyalty_ident_callback(tx),
            record_uid=tx_record_uid_callback(tx) if tx_record_uid_callback else None,
        )
        for tx in transactions
    ]


def make_audit_message(
    provider_slug: str,
    transactions: t.List[AuditTransaction],
    *,
    request: t.Optional[dict] = None,
    request_timestamp: t.Optional[str] = None,
    response: t.Optional[requests.Response] = None,
    response_timestamp: t.Optional[str] = None,
    blob_names: t.Optional[t.List[str]] = None,
) -> MessagePayload:
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

    return MessagePayload(provider_slug=provider_slug, transactions=transactions, audit_data=audit_data)


def queue_audit_message(message: MessagePayload) -> None:
    provider_slug = message["provider_slug"]
    if not settings.AUDIT_EXPORTS:
        log.warning(f"Not queueing {provider_slug} audit because AUDIT_EXPORTS is disabled.")
        log.debug(f"Audit payload:\n{message}")
    else:
        queue.add(message, provider=provider_slug, queue_name="tx_matching")
