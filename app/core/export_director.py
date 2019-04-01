from typing import cast

from app import tasks
from app.db import session
from app.exports.agents import BaseAgent
from app.exports.agents.registry import export_agents
from app.exports.models import PendingExport
from app.models import MatchedTransaction
from app.reporting import get_logger
from app.status import status_monitor

log = get_logger("export-director")


class ExportDirector:
    def handle_matched_transaction(self, matched_transaction_id: int) -> None:
        status_monitor.checkin(self)

        log.debug(f"Recieved matched transaction #{matched_transaction_id}.")
        matched_transaction: MatchedTransaction = session.query(MatchedTransaction).get(matched_transaction_id)
        loyalty_scheme = matched_transaction.merchant_identifier.loyalty_scheme

        log.debug(
            f"Creating pending export entry for loyalty scheme {loyalty_scheme.slug} "
            f"and matched transaction #{matched_transaction_id}."
        )
        pending_export = PendingExport(provider_slug=loyalty_scheme.slug, matched_transaction_id=matched_transaction_id)
        session.add(pending_export)
        session.commit()

        log.info(f"Sending trigger for single export agents: {pending_export}.")
        tasks.export_queue.enqueue(tasks.export_single_transaction, pending_export.id)

        session.close()

    def handle_pending_export(self, pending_export_id: int) -> None:
        pending_export = session.query(PendingExport).get(pending_export_id)
        agent = cast(BaseAgent, export_agents.instantiate(pending_export.provider_slug))

        log.info(f"Received {pending_export}, delegating to {agent}.")
        agent.handle_pending_export(pending_export)

        session.close()
