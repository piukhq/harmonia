import inspect

from app.exports.agents.bases.batch_export_agent import BatchExportAgent
from app.config import ConfigValue, KEY_PREFIX

SCHEDULE_KEY = f"{KEY_PREFIX}exports.agents.batch-example.schedule"


class BatchExampleAgent(BatchExportAgent):
    provider_slug = "batch-example"

    class Config:
        schedule = ConfigValue(SCHEDULE_KEY, "* * * * *")

    def help(self):
        return inspect.cleandoc(
            f"""
            This agent exports {self.provider_slug} transactions on a schedule of {self.Config.schedule}
            """
        )

    def export_all(self, *, once: bool = False):
        self.log.info(f"This is where we would batch export all {self.provider_slug} transactions.")
