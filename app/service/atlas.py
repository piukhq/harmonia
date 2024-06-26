import json
import typing as t
import uuid
from decimal import Decimal

import pendulum
import requests
import sentry_sdk

import settings
from app import models
from app.exports.models import ExportTransactionStatus
from app.reporting import get_logger, sanitise_logs
from app.service import exchange

log = get_logger("atlas")


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super().default(o)


class AuditTransaction(t.TypedDict):
    event_date_time: str
    user_id: str
    transaction_id: str
    transaction_date: str
    spend_amount: int
    spend_currency: str | None
    loyalty_id: str | None
    mid: str | None
    scheme_account_id: str | None
    encrypted_credentials: str | None
    status: str
    feed_type: str | None
    location_id: str | None
    merchant_internal_id: str | None
    payment_card_account_id: str | None
    settlement_key: str | None
    authorisation_code: str | None
    approval_code: str | None
    loyalty_identifier: str
    record_uid: str | None
    export_uid: str | uuid.UUID | None


class AuditData(t.TypedDict, total=False):
    request: t.Optional[t.Dict[str, t.Any]]
    response: t.Optional[t.Dict[str, t.Any]]
    file_names: t.Optional[t.List[str]]


class MessagePayload(t.TypedDict):
    provider_slug: str
    transactions: t.List[AuditTransaction]
    audit_data: AuditData
    retry_count: int


def make_audit_transactions(
    transactions: t.List[models.ExportTransaction],
    *,
    tx_loyalty_ident_callback: t.Callable[[models.ExportTransaction], str],
    tx_record_uid_callback: t.Optional[t.Callable[[models.ExportTransaction], t.Optional[str]]] = None,
) -> t.List[AuditTransaction]:
    return [
        AuditTransaction(
            event_date_time=pendulum.now().isoformat(),
            user_id=tx.user_id,
            transaction_id=tx.transaction_id,
            transaction_date=pendulum.instance(tx.transaction_date).to_datetime_string(),
            spend_amount=tx.spend_amount,
            spend_currency=tx.spend_currency,
            loyalty_id=tx.loyalty_id,
            mid=tx.mid,
            scheme_account_id=tx.scheme_account_id,
            encrypted_credentials=tx.credentials,
            status=ExportTransactionStatus.EXPORTED.name,
            feed_type=tx.feed_type.name if tx.feed_type else None,
            location_id=tx.location_id,
            merchant_internal_id=tx.merchant_internal_id,
            payment_card_account_id=tx.payment_card_account_id,
            settlement_key=tx.settlement_key,
            authorisation_code=tx.auth_code,
            approval_code=tx.approval_code,
            loyalty_identifier=tx_loyalty_ident_callback(tx),
            record_uid=tx_record_uid_callback(tx) if tx_record_uid_callback else None,
            export_uid=tx.export_uid if tx.export_uid else uuid.uuid4(),
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
    retry_count: int = 0,
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
            "body": sanitise_logs(body, provider_slug),
            "status_code": response.status_code,
            "timestamp": response_timestamp,
        }
    if blob_names:
        audit_data["file_names"] = blob_names

    return MessagePayload(
        provider_slug=provider_slug, transactions=transactions, audit_data=audit_data, retry_count=retry_count
    )


def make_audit_result(
    provider_slug: str,
    transactions: t.List[AuditTransaction],
    result: dict,
    result_timestamp: t.Optional[str] = None,
    source: t.Optional[t.List[str]] = None,
) -> MessagePayload:
    json_results = json.dumps(result, cls=DecimalEncoder, indent=4)
    audit_data = AuditData()
    audit_data["response"] = {
        "body": sanitise_logs(json_results, provider_slug),
        "status_code": 200,
        "timestamp": result_timestamp,
    }

    if source:
        audit_data["file_names"] = source

    return MessagePayload(provider_slug=provider_slug, transactions=transactions, audit_data=audit_data, retry_count=0)


def queue_audit_message(message: MessagePayload, destination="all") -> None:
    provider_slug = message["provider_slug"]
    if not settings.AUDIT_EXPORTS:
        log.warning(f"Not queueing {provider_slug} audit because AUDIT_EXPORTS is disabled.")
        log.debug(f"Audit payload:\n{message}")
    else:
        try:
            exchange.publish(t.cast(dict, message), provider=provider_slug, destination=destination)
        except Exception as ex:
            # Using a broad exception clause since we do not want any atlas fails or otherwise,
            # to affect other Harmonia processes. Logging will tell us about an issues.
            event_id = sentry_sdk.capture_exception()
            log.warning(f"Problem during Atlas audit process. {type(ex).__name__}. Sentry event ID: {event_id}")
