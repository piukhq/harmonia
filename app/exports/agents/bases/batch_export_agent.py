import typing as t

from sqlalchemy.orm import Load, joinedload

import settings
from app import db, models
from app.exports.agents import AgentExportData, BaseAgent
from app.scheduler import CronScheduler


class BatchExportAgent(BaseAgent):
    def run(self, *, once: bool = False):
        scheduler = CronScheduler(
            schedule_fn=lambda: self.Config.schedule, callback=self.export_all, logger=self.log  # type: ignore
        )

        if once:
            self.log.debug("Batch export agent running once.")
            scheduler.tick()
            return

        self.log.debug(f"Beginning schedule {scheduler}.")
        scheduler.run()

    def handle_pending_export(self, pending_export):
        self.log.debug(f"Ignoring {pending_export} for singular export.")

    def export(self, export_data: AgentExportData, *, session: db.Session):
        pass

    def export_all(self, *, session: db.Session, once: bool = False):
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

        self.log.debug(f"Exporting {len(pending_exports)} transactions.")

        for export_data in self.yield_export_data(transactions):
            if settings.SIMULATE_EXPORTS:
                self._save_to_blob(export_data)
            else:
                self.send_export_data(export_data)

            db.run_query(
                lambda: self._save_export_transactions(export_data, session=session),
                session=session,
                description="create export transactions from export data",
            )

        def delete_pending_exports():
            pending_exports_q.delete()
            session.commit()

        db.run_query(delete_pending_exports, session=session, description="delete pending exports")

    def yield_export_data(self, transactions: t.List[models.MatchedTransaction]):
        raise NotImplementedError("Override the yield_export_data method in your agent.")

    def send_export_data(self, export_data: AgentExportData):
        raise NotImplementedError("Override the send_export_data method in your agent.")
