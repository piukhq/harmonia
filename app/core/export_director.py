import uuid
from dataclasses import dataclass
from typing import Optional, cast

import pendulum

from app import db, tasks
from app.exports.agents import BaseAgent
from app.exports.agents.registry import export_agents
from app.exports.models import ExportTransaction, PendingExport
from app.feeds import FeedType
from app.registry import NoSuchAgent
from app.reporting import get_logger

log = get_logger("export-director")


@dataclass(frozen=True)
class ExportFields:
    transaction_id: str
    feed_type: Optional[FeedType]
    merchant_slug: str
    transaction_date: pendulum.DateTime
    spend_amount: int
    spend_currency: str
    loyalty_id: str
    mid: str
    primary_identifier: str
    location_id: str
    merchant_internal_id: str
    user_id: int
    scheme_account_id: int
    payment_card_account_id: Optional[int]
    credentials: str
    settlement_key: Optional[str]
    last_four: Optional[str]
    expiry_month: Optional[int]
    expiry_year: Optional[int]
    payment_provider_slug: Optional[str]
    auth_code: str
    approval_code: str
    extra_fields: dict


def create_export(fields: ExportFields, *, session: db.Session) -> None:
    """
    Utility method to create an export transaction record and queue up an export job for it.
    """

    def add_export_transaction():
        export_transaction = ExportTransaction(
            transaction_id=fields.transaction_id,
            feed_type=fields.feed_type,
            provider_slug=fields.merchant_slug,
            transaction_date=fields.transaction_date,
            spend_amount=fields.spend_amount,
            spend_currency=fields.spend_currency,
            loyalty_id=fields.loyalty_id,
            mid=fields.mid,
            primary_identifier=fields.mid,
            location_id=fields.location_id,
            merchant_internal_id=fields.merchant_internal_id,
            user_id=fields.user_id,
            scheme_account_id=fields.scheme_account_id,
            payment_card_account_id=fields.payment_card_account_id,
            credentials=fields.credentials,
            settlement_key=fields.settlement_key,
            last_four=fields.last_four,
            expiry_month=fields.expiry_month,
            expiry_year=fields.expiry_year,
            payment_provider_slug=fields.payment_provider_slug,
            auth_code=fields.auth_code,
            approval_code=fields.approval_code,
            export_uid=uuid.uuid4(),
        )
        session.add(export_transaction)
        session.commit()

        return export_transaction

    export_transaction = db.run_query(add_export_transaction, session=session, description="create export transaction")
    tasks.export_queue.enqueue(tasks.export_transaction, export_transaction.id)


class ExportDirector:
    def handle_export_transaction(self, export_transaction_id: int, *, session: db.Session) -> None:
        log.debug(f"Recieved export transaction #{export_transaction_id}.")
        export_transaction: ExportTransaction = db.run_query(
            lambda: session.query(ExportTransaction).get(export_transaction_id),
            session=session,
            read_only=True,
            description="find export transaction",
        )

        if export_transaction is None:
            log.warning(f"Failed to load export transaction #{export_transaction_id} - record may have been deleted.")
            return

        loyalty_scheme = export_transaction.provider_slug

        log.debug(
            f"Creating pending export entry for loyalty scheme {loyalty_scheme} "
            f"and export transaction #{export_transaction_id}."
        )

        def add_pending_export():
            pending_export = PendingExport(provider_slug=loyalty_scheme, export_transaction_id=export_transaction_id)
            session.add(pending_export)
            session.commit()
            return pending_export

        pending_export = db.run_query(add_pending_export, session=session, description="create pending export")

        log.info(f"Sending trigger for singular export agents: {pending_export}.")
        tasks.export_queue.enqueue(tasks.export_singular_transaction, pending_export.id)

    def handle_pending_export(self, pending_export_id: int, *, session: db.Session) -> None:
        pending_export = db.run_query(
            lambda: session.query(PendingExport).get(pending_export_id),
            session=session,
            read_only=True,
            description="find pending export",
        )

        if pending_export is None:
            log.warning(f"Failed to load pending export #{pending_export_id} - record may have been deleted.")
            return

        try:
            agent = cast(BaseAgent, export_agents.instantiate(pending_export.provider_slug))
        except NoSuchAgent:
            log.debug(
                f"No export agent is registered for slug {pending_export.provider_slug}. Skipping {pending_export}"
            )
            return

        log.info(f"Received {pending_export}, delegating to {agent}.")
        agent.handle_pending_export(pending_export, session=session)
