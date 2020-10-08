import typing as t
from contextlib import ExitStack

import settings
from app import db, models
from app.exports.agents import AgentExportData, BaseAgent
from app.prometheus import bink_prometheus
from app.scheduler import CronScheduler
from sqlalchemy.orm import Load, joinedload


class BatchExportAgent(BaseAgent):
    def __init__(self):
        super().__init__()

        self.bink_prometheus = bink_prometheus

    def run(self):
        scheduler = CronScheduler(
            schedule_fn=lambda: self.Config.schedule, callback=self.callback, logger=self.log  # type: ignore
        )

        self.log.debug(f"Beginning schedule {scheduler}.")
        scheduler.run()

    def handle_pending_export(self, pending_export, *, session: db.Session):
        self.log.debug(f"Ignoring {pending_export} for singular export.")

    def export(self, export_data: AgentExportData, *, session: db.Session):
        pass

    def callback(self):
        with db.session_scope() as session:
            self.export_all(session=session)

    def export_all(self, *, session: db.Session):
        pending_exports_q = (
            session.query(models.PendingExport)
            .options(
                joinedload(models.PendingExport.matched_transaction, innerjoin=True)
                .joinedload(models.MatchedTransaction.payment_transaction, innerjoin=True)
                .joinedload(models.PaymentTransaction.user_identity, innerjoin=True),
                Load(models.PendingExport).raiseload("*"),
            )
            .filter(models.PendingExport.provider_slug == self.provider_slug)
        )

        pending_exports = pending_exports_q.all()
        transactions = [pe.matched_transaction for pe in pending_exports]

        if not transactions:
            return  # nothing to export

        self.log.debug(f"Exporting {len(pending_exports)} transactions.")

        for export_data in self.yield_export_data(transactions, session=session):
            if settings.SIMULATE_EXPORTS:
                self._save_to_blob(export_data)
            else:
                self._update_metrics(export_data)

            db.run_query(
                lambda: self._save_export_transactions(export_data, session=session),
                session=session,
                description="create export transactions from export data",
            )

        def delete_pending_exports():
            pending_exports_q.delete()
            session.commit()

        db.run_query(
            delete_pending_exports, session=session, description="delete pending exports",
        )

    def _update_metrics(self, export_data: AgentExportData, session=None) -> None:
        """
        Update any Prometheus metrics this agent might have
        """
        # Use the Prometheus request latency context manager if we have one. This must be the first method
        # call of course
        with ExitStack() as stack:
            self.bink_prometheus.use_histogram_context_manager(
                agent=self,
                histogram_name="request_latency",
                context_manager_stack=stack,
                process_type="export",
                slug=self.provider_slug,
            )
            self.bink_prometheus.increment_counter(
                agent=self,
                counter_name="requests_sent",
                increment_by=1,
                process_type="export",
                slug=self.provider_slug,
            )
            try:
                self.export(export_data, session=session)
            except Exception:
                self.bink_prometheus.increment_counter(
                    agent=self,
                    counter_name="failed_requests",
                    increment_by=1,
                    process_type="export",
                    slug=self.provider_slug,
                )
                raise
            else:
                self.bink_prometheus.increment_counter(
                    agent=self,
                    counter_name="transactions",
                    increment_by=len(export_data.transactions),
                    process_type="export",
                    slug=self.provider_slug,
                )

    def yield_export_data(
        self, transactions: t.List[models.MatchedTransaction], *, session: db.Session
    ) -> t.Iterable[AgentExportData]:
        raise NotImplementedError("Override the yield_export_data method in your agent.")

    def send_export_data(self, export_data: AgentExportData) -> None:
        raise NotImplementedError("Override the send_export_data method in your agent.")
