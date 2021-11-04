from typing import cast

from app import db, tasks
from app.exports.agents import BaseAgent
from app.exports.agents.registry import export_agents
from app.exports.models import ExportTransaction, PendingExport
from app.registry import NoSuchAgent
from app.reporting import get_logger
from app.status import status_monitor

log = get_logger("export-director")


class ExportDirector:
    def handle_export_transaction(self, export_transaction_id: int, *, session: db.Session) -> None:
        status_monitor.checkin(self)

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
