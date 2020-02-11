from app.exports.agents import BaseAgent
from app.scheduler import CronScheduler

import settings


class BatchExportAgent(BaseAgent):
    def run(self, *, once: bool = False):
        scheduler = CronScheduler(
            schedule_fn=lambda: self.Config.schedule, callback=self.export_all, logger=self.log  # type: ignore
        )

        if once:
            scheduler.tick()
            return

        scheduler.run()

    def export(self, matched_transaction_id: int):
        return

    def export_all(self, *, once: bool = False):
        for export_data in self.yield_export_data():
            if settings.EXPORT_TO_FILE:
                self._save_to_file(export_data["body"])
                return
            else:
                self.send_export_data(export_data)

    def yield_export_data(self):
        raise NotImplementedError(
            "Override the yield_export_data method in your agent."
        )

    def send_export_data(self, export_data: dict):
        raise NotImplementedError(
            "Override the send_export_data method in your agent."
        )
