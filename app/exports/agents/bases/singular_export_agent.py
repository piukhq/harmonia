from contextlib import ExitStack

import settings
from app import db, models
from app.exports.agents import BaseAgent
from app.exports.agents.bases.base import AgentExportData
from app.prometheus import BinkPrometheus
from app.status import status_monitor
from sqlalchemy.orm import Session


class SingularExportAgent(BaseAgent):
    def run(self):
        raise NotImplementedError(
            f"{type(self).__name__} is a singular export agent and as such must be run via the import director."
        )

    def export(self, export_data: AgentExportData, *, session: db.Session):
        raise NotImplementedError(
            "Override the export method in your agent to act as the entry point into the singular export process."
        )

    def export_all(self, *, session: db.Session):
        raise NotImplementedError(
            f"{type(self).__name__} is a singular export agent and as such does not support batch exports."
        )

    def find_matched_transaction(
        self, pending_export: models.PendingExport, *, session: db.Session
    ) -> models.MatchedTransaction:
        def find_transaction():
            return session.query(models.MatchedTransaction).get(pending_export.matched_transaction_id)

        matched_transaction = db.run_query(
            find_transaction, session=session, read_only=True, description="load matched transaction",
        )

        if matched_transaction is None:
            self.log.warning(
                f"Failed to load matched transaction #{pending_export.matched_transaction_id}. "
                "Record may have been deleted."
            )
            raise db.NoResultFound

        return matched_transaction

    def handle_pending_export(self, pending_export: models.PendingExport, *, session: db.Session):
        status_monitor.checkin(self)

        self.log.info(f"Handling {pending_export}.")

        try:
            matched_transaction = self.find_matched_transaction(pending_export, session=session)
        except db.NoResultFound:
            self.log.warning(
                f"The export agent failed to load its matched transaction. {pending_export} will be discarded."
            )
        else:
            self.log.info(f"{type(self).__name__} handling {matched_transaction}.")
            export_data = self.make_export_data(matched_transaction)

            if settings.SIMULATE_EXPORTS:
                self._save_to_blob(export_data)
            else:
                self._update_metrics(export_data=export_data, session=session)

            self._save_export_transactions(export_data, session=session)

        self.log.info(f"Removing pending export {pending_export}.")

        def delete_pending_export():
            session.delete(pending_export)
            session.commit()

        db.run_query(delete_pending_export, session=session, description="delete pending export")

    def _update_metrics(self, export_data: AgentExportData, session: Session) -> None:
        """
        Update (optional) Prometheus metrics
        """
        # Use the Prometheus request latency context manager if we have one
        with ExitStack() as stack:
            context_manager = getattr(self, "request_latency_histogram", None)
            if context_manager:
                stack.enter_context(context_manager.time())
            BinkPrometheus.increment_counter(obj=self, counter_name="requests_sent", increment_by=1)
            try:
                self.export(export_data, session=session)
            except Exception:
                BinkPrometheus.increment_counter(obj=self, counter_name="failed_requests_counter", increment_by=1)
                raise
            else:
                BinkPrometheus.increment_counter(obj=self, counter_name="transactions_counter", increment_by=1)

    def make_export_data(self, matched_transaction: models.MatchedTransaction) -> AgentExportData:
        raise NotImplementedError("Override the make export data method in your export agent")
