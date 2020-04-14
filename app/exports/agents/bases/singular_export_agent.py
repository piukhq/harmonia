import settings
from app import db
from app.exports.agents import BaseAgent
from app.exports.agents.bases.base import AgentExportData
from app.models import PendingExport
from app.status import status_monitor


class SingularExportAgent(BaseAgent):
    def run(self, *, once: bool = False):
        self.export_all()

    def export(self, export_data: AgentExportData):
        raise NotImplementedError(
            "Override the export method in your agent to act as the entry point into the singular export process."
        )

    def export_all(self):
        raise NotImplementedError(
            f"{type(self).__name__} is a singular export agent and as such does not support batch exports."
        )

    def handle_pending_export(self, pending_export: PendingExport):
        status_monitor.checkin(self)

        self.log.info(f"Handling {pending_export}.")

        try:
            export_data = self.make_export_data(pending_export.matched_transaction_id)
        except db.NoResultFound:
            self.log.warning(
                f"The export agent failed to load its matched transaction. {pending_export} will be discarded."
            )
        else:
            if settings.SIMULATE_EXPORTS:
                self._save_to_blob(export_data)
            else:
                self.export(export_data)
            self._save_export_transactions(export_data)

        self.log.info(f"Removing pending export {pending_export}.")

        def delete_pending_export():
            db.session.delete(pending_export)
            db.session.commit()

        db.run_query(delete_pending_export, description="delete pending export")

    def make_export_data(self, matched_transaction_id: int) -> AgentExportData:
        raise NotImplementedError("Override the make export data method in your export agent")
