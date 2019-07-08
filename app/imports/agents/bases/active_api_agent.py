import requests

from app.imports.agents import BaseAgent
from app.scheduler import CronScheduler


class ActiveAPIAgent(BaseAgent):
    def run(self, *, once: bool = False):
        scheduler = CronScheduler(
            schedule_fn=lambda: self.Config.schedule, callback=self.do_import, logger=self.log  # type: ignore
        )

        if once is True:
            scheduler.tick()
            return

        scheduler.run()

    def do_import(self):
        resp = requests.get(self.url)
        resp.raise_for_status()
        transactions_data, errors = self.schema.load(resp.json(), many=True)
        if errors:
            self.log.error(f"Failed to load transactions data from API response: {errors}")
        elif transactions_data:
            self._import_transactions(transactions_data, source=self.url)
