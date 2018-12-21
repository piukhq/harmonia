from app.exports.agents.bases.base import BaseAgent
from app.scheduler import CronScheduler


class BatchExportAgent(BaseAgent):
    def run(self, *, once: bool = False, debug: bool = False):
        self.debug = debug

        scheduler = CronScheduler(
            schedule_fn=lambda: self.Config.schedule,  # type: ignore
            callback=self.export_all,
            logger=self.log,
        )

        if once:
            scheduler.tick()
            return

        scheduler.run(raise_exceptions=debug)

    def export(self, matched_transaction_id: int):
        return

    def export_all(self, *, once: bool = False, debug: bool = False):
        raise NotImplementedError(
            "Override the export_all method in your agent to act as the entry point "
            "into the batch export process."
        )
