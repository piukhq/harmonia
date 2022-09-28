import typing as t

import settings
from app.models import ExportTransaction
from app.reporting import get_logger
from app.service import queue

log = get_logger(__name__)


class ExportedTransaction(t.TypedDict):
    event_type: str
    event_date_time: str
    internal_user_ref: str
    transaction_id: str
    provider_slug: str
    transaction_date: str
    spend_amount: int
    spend_currency: str
    loyalty_id: str
    mid: str
    scheme_account_id: int
    credentials: str
    status: str
    feed_type: t.Optional[str]
    location_id: t.Optional[str]
    merchant_internal_id: t.Optional[int]
    payment_card_account_id: t.Optional[str]
    settlement_key: t.Optional[str]
    authorisation_code: t.Optional[str]
    approval_code: t.Optional[str]


def exported_event(transactions: t.List[ExportTransaction]):
    # convert the passed in data to a message body dict.
    for transaction in transactions:
        provider_slug = transaction.provider_slug
        exported_transaction = ExportedTransaction(
            event_type="transaction.exported",
            event_date_time=transaction.created_at.isoformat(),
            internal_user_ref=transaction.user_id,
            transaction_id=transaction.transaction_id,
            provider_slug=provider_slug,
            transaction_date=transaction.transaction_date.isoformat(),
            spend_amount=transaction.spend_amount,
            spend_currency=transaction.spend_currency,
            loyalty_id=transaction.loyalty_id,
            mid=transaction.mid,
            scheme_account_id=transaction.scheme_account_id,
            credentials=transaction.credentials,
            status=transaction.status.name if transaction.status else None,
            feed_type=transaction.feed_type.name if transaction.feed_type else None,
            location_id=transaction.location_id,
            merchant_internal_id=transaction.merchant_internal_id,
            payment_card_account_id=transaction.payment_card_account_id,
            settlement_key=transaction.settlement_key,
            authorisation_code=transaction.auth_code,
            approval_code=transaction.approval_code,
        )

        # Send the message via a rabbit queue
        queue_message(dict(exported_transaction))


def queue_message(message: dict) -> None:
    provider_slug = message["provider_slug"]
    if not settings.AUDIT_EXPORTS:
        log.warning(f"Not queueing {provider_slug} data warehouse events because AUDIT_EXPORTS is disabled.")
        log.debug(f"Export data payload:\n{message}")
    else:
        queue.add(message, provider=provider_slug, queue_name="tx_export_dw")
