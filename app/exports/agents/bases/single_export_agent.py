from app.db import Session
from app.exports.agents.bases.base import BaseAgent
from app.models import PendingExport
from app.queues import pending_export_queue
from app.status import status_monitor

session = Session()


class SingleExportAgent(BaseAgent):
    def export(self, matched_transaction_id: int, *, once: bool = False):
        raise NotImplementedError(
            "Override the export method in your agent to act as the entry point "
            "into the singular export process."
        )

    def on_pending_export(self, pending_export_id: int, message_headers: dict) -> bool:
        status_monitor.checkin(self)
        pending_export = session.query(PendingExport).get(pending_export_id)

        self.log.info(f"Handling {pending_export}.")
        try:
            self.export(pending_export.matched_transaction_id)
        except Exception as ex:
            if self.debug:
                raise
            self.log.warning(f"Raised {repr(ex)}! Export should be requeued.")
            return False
        else:
            self.log.info(f"Removing pending export {pending_export}.")
            session.delete(pending_export)
            session.commit()
            return True

    def run(self, *, once: bool = False) -> None:
        self.log.info(f"{type(self).__name__} commencing export feed consumption.")
        pending_export_queue.pull(
            self.on_pending_export, raise_exceptions=self.debug, once=once
        )
