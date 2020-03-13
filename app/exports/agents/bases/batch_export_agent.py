from app.exports.agents import BaseAgent, AgentExportData
from app.scheduler import CronScheduler
from app import db

import settings


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

    def export(self, export_data: AgentExportData):
        pass

    def export_all(self, *, once: bool = False):
        self.log.debug("Exporting all transactions.")
        breakpoint()
        for export_data in self.yield_export_data():
            if settings.SIMULATE_EXPORTS:
                self._save_to_blob(export_data)
            else:
                self.send_export_data(export_data)

            db.run_query(
                lambda: self._save_export_transactions(export_data),
                description="create export transactions from export data",
            )

    def yield_export_data(self):
        raise NotImplementedError("Override the yield_export_data method in your agent.")

    def send_export_data(self, export_data: AgentExportData):
        raise NotImplementedError("Override the send_export_data method in your agent.")
