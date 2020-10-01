import settings
from app import db, models
from app.exports.agents import BaseAgent
from app.exports.agents.bases.base import AgentExportData
from app.status import status_monitor
from prometheus_client import Counter, Histogram


class SingularExportAgent(BaseAgent):

    def __init__(self) -> None:
        super().__init__()
        provider_slug = self.provider_slug.replace("-", "_")
        self.exported_transactions_counter = Counter(f"exported_transactions_single_{provider_slug}",
                                                     f"Number of transactions sent to {provider_slug}")
        self.requests_sent_counter = Counter(f"requests_sent_single_{provider_slug}",
                                             f"Number of requests sent to {provider_slug}")
        self.failed_requests_counter = Counter(f"failed_requests_single_{provider_slug}",
                                               f"Number of failed requests to {provider_slug}")
        self.request_latency = Histogram(f"request_latency_seconds_single_{provider_slug}",
                                         f"Request latency seconds for {provider_slug}")

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
            find_transaction, session=session, read_only=True, description="load matched transaction"
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
                with self.request_latency.time():
                    try:
                        self.export(export_data, session=session)
                    except Exception:
                        self.failed_requests_counter.inc()
                        raise
                    else:
                        self.exported_transactions_counter.inc()
            self._save_export_transactions(export_data, session=session)

        self.log.info(f"Removing pending export {pending_export}.")

        def delete_pending_export():
            session.delete(pending_export)
            session.commit()

        db.run_query(delete_pending_export, session=session, description="delete pending export")

    def make_export_data(self, matched_transaction: models.MatchedTransaction) -> AgentExportData:
        raise NotImplementedError("Override the make export data method in your export agent")
