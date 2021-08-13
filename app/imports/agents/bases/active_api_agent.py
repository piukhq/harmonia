from functools import cached_property

import marshmallow
import requests

from app import db
from app.imports.agents import BaseAgent
from app.scheduler import CronScheduler


class ActiveAPIAgent(BaseAgent):
    @cached_property
    def schedule(self):
        with db.session_scope() as session:
            schedule = self.config.get("schedule", session=session)
        return schedule

    def run(self):
        scheduler = CronScheduler(
            name="active-api-agent",
            schedule_fn=lambda: self.schedule,
            callback=self.do_import,
            logger=self.log,  # type: ignore
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
