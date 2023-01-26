import json
import typing as t

import pendulum
import requests
import sentry_sdk

import settings
from app import models
from app.reporting import get_logger
from app.service import exchange

log = get_logger("atlas")


class AuditTransaction(t.TypedDict):
    transaction_id: str
    user_id: str
    spend_amount: int
    transaction_date: str
    loyalty_identifier: str
    record_uid: t.Optional[str]
    scheme_account_id: str
    encrypted_credentials: str
    status: str
    feed_type: str
    location_id: str
    merchant_internal_id: str
    settlement_key: str


class AuditData(t.TypedDict, total=False):
    request: t.Optional[t.Dict[str, t.Any]]
    response: t.Optional[t.Dict[str, t.Any]]
    file_names: t.Optional[t.List[str]]


class MessagePayload(t.TypedDict):
    provider_slug: str
    transactions: t.List[AuditTransaction]
    audit_data: AuditData


def make_audit_transactions(
    transactions: t.List[models.ExportTransaction],
    *,
    tx_loyalty_ident_callback: t.Callable[[models.ExportTransaction], str],
    tx_record_uid_callback: t.Optional[t.Callable[[models.ExportTransaction], t.Optional[str]]] = None,
) -> t.List[AuditTransaction]:
    return [
        AuditTransaction(
            transaction_id=tx.transaction_id,
            user_id=tx.user_id,
            spend_amount=tx.spend_amount,
            transaction_date=pendulum.instance(tx.transaction_date).to_datetime_string(),
            loyalty_identifier=tx_loyalty_ident_callback(tx),
            record_uid=tx_record_uid_callback(tx) if tx_record_uid_callback else None,
            scheme_account_id=tx.scheme_account_id,
            encrypted_credentials=tx.credentials,
            status=tx.status.name if tx.status else None,
            feed_type=tx.feed_type.name if tx.feed_type else None,
            location_id=tx.location_id,
            merchant_internal_id=tx.merchant_internal_id,
            settlement_key=tx.settlement_key,
        )
        for tx in transactions
    ]


def make_audit_message(
    provider_slug: str,
    transactions: t.List[AuditTransaction],
    *,
    request: t.Optional[t.Union[dict, str]] = None,
    request_timestamp: t.Optional[str] = None,
    response: t.Optional[requests.Response] = None,
    response_timestamp: t.Optional[str] = None,
    blob_names: t.Optional[t.List[str]] = None,
    request_url: t.Optional[str] = None,
) -> MessagePayload:
    audit_data = AuditData()
    if request is not None:
        if type(request) == str:
            request = json.loads(request)
        request["request_url"] = request_url  # type: ignore
        audit_data["request"] = {"body": request, "timestamp": request_timestamp}

    if response is not None:
        try:
            body = response.json()
        except ValueError:
            # we assume no binary responses from merchant APIs.
            # if we do get a binary response, we will need to consider base64 encoding
            # to make it json serializable.
            body = response.text

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
        try:
            exchange.publish(t.cast(dict, message), provider=provider_slug)
        except Exception as ex:
            # Using a broad exception clause since we do not want any atlas fails or otherwise,
            # to affect other Harmonia processes. Logging will tell us about an issues.
            event_id = sentry_sdk.capture_exception()
            log.warning(f"Problem during Atlas audit process. {type(ex).__name__}. Sentry event ID: {event_id}")
