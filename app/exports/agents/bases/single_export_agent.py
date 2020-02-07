from app import db
from app.exports.agents import BaseAgent
from app.models import PendingExport
from app.status import status_monitor

import settings


class SingleExportAgent(BaseAgent):
    def run(self, *, once: bool = False):
        self.export_all()

    def export(self, export_data: dict):
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
        export_data = self.make_export_data(pending_export.matched_transaction_id)
        if settings.EXPORT_TO_FILE:
            self.save_export_data_to_file(export_data)
            return
        self.export(export_data)

        self.log.info(f"Removing pending export {pending_export}.")

        def delete_pending_export():
            db.session.delete(pending_export)
            db.session.commit()

        db.run_query(delete_pending_export, description="delete pending export")
