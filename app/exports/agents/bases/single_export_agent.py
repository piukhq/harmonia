from app import db
from app.exports.agents import BaseAgent
from app.models import PendingExport
from app.status import status_monitor


class SingleExportAgent(BaseAgent):
    def run(self, *, once: bool = False):
        self.export_all()

    def export(self, matched_transaction_id: int):
        raise NotImplementedError(
            "Override the export method in your agent to act as the entry point into the singular export process."
        )

    def export_all(self):
        raise NotImplementedError(
            f"{type(self).__name__} is a single export agent and as such does not support batch exports."
        )

    def handle_pending_export(self, pending_export: PendingExport) -> None:
        status_monitor.checkin(self)

        self.log.info(f"Handling {pending_export}.")
        self.export(pending_export.matched_transaction_id)

        self.log.info(f"Removing pending export {pending_export}.")

        def delete_pending_export():
            db.session.delete(pending_export)
            db.session.commit()

        db.run_query(delete_pending_export, description="delete pending export")
