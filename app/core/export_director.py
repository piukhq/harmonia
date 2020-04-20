from typing import cast

from app import tasks, db
from app.exports.agents import BaseAgent
from app.exports.agents.registry import export_agents
from app.exports.models import PendingExport
from app.models import MatchedTransaction
from app.reporting import get_logger
from app.status import status_monitor
from app.registry import RegistryError

log = get_logger("export-director")


class ExportDirector:
    def handle_matched_transaction(self, matched_transaction_id: int, *, session: db.Session) -> None:
        status_monitor.checkin(self)

        log.debug(f"Recieved matched transaction #{matched_transaction_id}.")
        matched_transaction: MatchedTransaction = db.run_query(
            lambda: session.query(MatchedTransaction).get(matched_transaction_id),
            session=session,
            read_only=True,
            description="find matched transaction",
        )

        if matched_transaction is None:
            log.warning(f"Failed to load matched transaction #{matched_transaction_id} - record may have been deleted.")
            return

        loyalty_scheme = matched_transaction.merchant_identifier.loyalty_scheme

        log.debug(
            f"Creating pending export entry for loyalty scheme {loyalty_scheme.slug} "
            f"and matched transaction #{matched_transaction_id}."
        )

        def add_pending_export():
            pending_export = PendingExport(
                provider_slug=loyalty_scheme.slug, matched_transaction_id=matched_transaction_id
            )
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
        except RegistryError:
            log.debug(
                f"No export agent is registered for slug {pending_export.provider_slug}. Skipping {pending_export}"
            )
            return

        log.info(f"Received {pending_export}, delegating to {agent}.")
        agent.handle_pending_export(pending_export, session=session)
