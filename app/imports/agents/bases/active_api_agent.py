from time import sleep

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import requests

from app.imports.agents.bases.base import BaseAgent, log


class ActiveAPIAgent(BaseAgent):
    @staticmethod
    def _get_trigger(schedule):
        try:
            return CronTrigger.from_crontab(schedule)
        except ValueError:
            log.error((f"Schedule '{schedule}' is not in a recognised format! "
                       f"Reverting to default of '* * * * *'."))
            return CronTrigger.from_crontab('* * * * *')

    def run(self, immediate=False, debug=False):
        self.debug = debug

        if immediate:
            self.tick()
            return

        scheduler = BackgroundScheduler()

        schedule = self.Config.schedule
        job = scheduler.add_job(self.tick, trigger=self._get_trigger(schedule))
        scheduler.start()

        try:
            while scheduler.running:
                new_schedule = self.Config.schedule
                if new_schedule != schedule:
                    log.debug(f"Schedule has been changed from {schedule} to {new_schedule}! Rescheduling...")
                    schedule = new_schedule
                    job.reschedule(self._get_trigger(schedule))
                sleep(5)
        except KeyboardInterrupt:
            log.debug('Shutting down...')
            scheduler.shutdown()
            log.debug('Done!')

    def tick(self):
        try:
            self.do_import()
        except Exception as e:
            if self.debug:
                raise
            else:
                log.error(e)

    def do_import(self):
        resp = requests.get(self.url)
        resp.raise_for_status()
        transactions_data = self.get_schema().load(resp.json(), many=True)
        self._import_transactions(transactions_data)
