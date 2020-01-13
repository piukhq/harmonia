import requests
import marshmallow

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

        try:
            transactions_data = self.schema.load(resp.json(), many=True)
        except marshmallow.ValidationError as ex:
            self.log.error(f"Failed to load transactions data from API response: {ex.messages}")
        else:
            self._import_transactions(transactions_data, source=self.url)
