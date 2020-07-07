import requests
import marshmallow

from app.imports.agents import BaseAgent
from app.scheduler import CronScheduler
from app import db


class ActiveAPIAgent(BaseAgent):
    def run(self):
        scheduler = CronScheduler(
            schedule_fn=lambda: self.Config.schedule, callback=self.do_import, logger=self.log  # type: ignore
        )

        scheduler.run()

    def do_import(self):
        resp = requests.get(self.url)
        resp.raise_for_status()

        try:
            transactions_data = self.schema.load(resp.json(), many=True)
        except marshmallow.ValidationError as ex:
            self.log.error(f"Failed to load transactions data from API response: {ex.messages}")
        else:
            with db.session_scope() as session:
                list(self._import_transactions(transactions_data, session=session, source=self.url))
