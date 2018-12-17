from app import queues
from app.db import Session
from app.exports.models import PendingExport
from app.models import MatchedTransaction
from app.reporting import get_logger
from app.status import status_monitor

log = get_logger("export-director")
session = Session()


class ExportDirector:
    def on_matched_transaction(
        self, matched_transaction_id: int, headers: dict
    ) -> bool:
        status_monitor.checkin(self)

        log.debug(f"Recieved matched transaction #{matched_transaction_id}.")
        matched_transaction: MatchedTransaction = session.query(MatchedTransaction).get(
            matched_transaction_id
        )
        loyalty_scheme = matched_transaction.merchant_identifier.loyalty_scheme

        log.debug(
            f"Creating pending export entry for loyalty scheme {loyalty_scheme.slug} "
            f"and matched transaction #{matched_transaction_id}."
        )
        pending_export = PendingExport(
            provider_slug=loyalty_scheme.slug,
            matched_transaction_id=matched_transaction_id,
        )
        session.add(pending_export)
        session.commit()

        log.debug(
            f"Notifying pending export queue of pending export #{pending_export.id}."
        )
        queues.pending_export_queue.push({"pending_export_id": pending_export.id})

        return True

    def enter_loop(self, *, debug: bool = False, once: bool = False) -> None:
        queues.export_queue.pull(
            self.on_matched_transaction, raise_exceptions=debug, once=once
        )
