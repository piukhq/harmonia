import requests

from app.imports.agents.bases.base import BaseAgent
from app.scheduler import CronScheduler


class ActiveAPIAgent(BaseAgent):
    def run(self, *, once: bool = False):
        scheduler = CronScheduler(
            schedule_fn=lambda: self.Config.schedule,  # type: ignore
            callback=self.do_import,
            logger=self.log,
        )

        if once is True:
            scheduler.tick()
            return

        scheduler.run(raise_exceptions=self.debug)

    def do_import(self):
        resp = requests.get(self.url)
        resp.raise_for_status()
        transactions_data = self.schema.load(resp.json(), many=True)
        if transactions_data:
            self._import_transactions(transactions_data, source=self.url)
