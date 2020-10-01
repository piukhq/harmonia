import typing as t

import settings
from app import db, models
from app.exports.agents import AgentExportData, BaseAgent
from app.scheduler import CronScheduler
from prometheus_client import Counter, Histogram
from requests import HTTPError
from sqlalchemy.orm import Load, joinedload


class BatchExportAgent(BaseAgent):

    def __init__(self) -> None:
        super().__init__()
        provider_slug = self.provider_slug.replace("-", "_")
        self.exported_transactions_counter = Counter(f"exported_transactions_batch_{provider_slug}",
                                                     f"Number of transactions sent to {provider_slug}")
        self.requests_sent_counter = Counter(f"requests_sent_batch_{provider_slug}",
                                             f"Number of requests sent to {provider_slug}")
        self.failed_requests_counter = Counter(f"failed_requests_batch_{provider_slug}",
                                               f"Number of failed requests to {provider_slug}")
        self.request_latency = Histogram(f"request_latency_seconds_batch_{provider_slug}",
                                         f"Request latency seconds for {provider_slug}")

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
                with self.request_latency.time():
                    try:
                        self.send_export_data(export_data)
                    except HTTPError:
                        self.failed_requests_counter.inc()
                        raise
                    else:
                        self.exported_transactions_counter.inc()
            db.run_query(
                lambda: self._save_export_transactions(export_data, session=session),
                session=session,
                description="create export transactions from export data",
            )

        def delete_pending_exports():
            pending_exports_q.delete()
            session.commit()

        db.run_query(delete_pending_exports, session=session, description="delete pending exports")

    def yield_export_data(
        self, transactions: t.List[models.MatchedTransaction], *, session: db.Session
    ) -> t.Iterable[AgentExportData]:
        raise NotImplementedError("Override the yield_export_data method in your agent.")

    def send_export_data(self, export_data: AgentExportData) -> None:
        raise NotImplementedError("Override the send_export_data method in your agent.")
