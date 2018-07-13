from time import sleep

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import requests

from app.imports.agents.bases.base import BaseAgent, ImportTransactionAlreadyExistsError
from app.status import status_monitor
from app.reporting import get_logger
from app.queues import import_queue


log = get_logger('agnt')


class ActiveAPIAgent(BaseAgent):
    @staticmethod
    def _get_trigger(schedule):
        try:
            return CronTrigger.from_crontab(schedule)
        except ValueError:
            log.error(
                (f"Schedule '{schedule}' is not in a recognised format! "
                 f"Reverting to default of '* * * * *'."))
            return CronTrigger.from_crontab('* * * * *')

    def run(self, immediate=False, debug=False):
        self.debug = debug

        if immediate:
            self.tick()
            return

        scheduler = BackgroundScheduler()

        schedule = self.Config.schedule
        job = scheduler.add_job(
            self.tick,
            trigger=self._get_trigger(schedule))
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
        status_monitor.scheduled_task_checkin(self.__class__.__name__)

        try:
            self.do_import()
        except Exception as e:
            if self.debug:
                raise
            else:
                log.error(e)

    def get_schema(self):
        return self.schema_class()

    def do_import(self):
        resp = requests.get(self.url)
        resp.raise_for_status()

        schema = self.get_schema()
        transactions, errors = schema.load(resp.json(), many=True)

        name = self.__class__.__name__

        if errors:
            log.error(f"Import translation for {name} failed: {errors}")
            return
        else:
            log.info(f"Import translation successful for {name}: {len(transactions)} transactions loaded.")

        for transaction in transactions:
            try:
                self._create_import_transaction(schema, transaction)
            except ImportTransactionAlreadyExistsError:
                log.info('Not pushing transaction to the import queue as it appears to already exist.')
            else:
                log.info('Pushing transaction to the import queue.')
                import_queue.push([schema.to_scheme_transaction(tx) for tx in transactions], many=True)
