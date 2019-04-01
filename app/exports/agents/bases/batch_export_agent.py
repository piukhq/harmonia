from app.exports.agents import BaseAgent
from app.scheduler import CronScheduler


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
        raise NotImplementedError(
            "Override the export_all method in your agent to act as the entry point into the batch export process."
        )
