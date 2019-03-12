import typing as t
from logging import Logger
from time import sleep

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.reporting import get_logger
import settings


class CronScheduler:
    def __init__(self, *, schedule_fn: t.Callable, callback: t.Callable, logger: Logger = None):
        self.schedule_fn = schedule_fn
        self.callback = callback
        self.log = logger if logger is not None else get_logger("cron-scheduler")

    def _get_trigger(self, schedule):
        try:
            return CronTrigger.from_crontab(schedule)
        except ValueError:
            self.log.error(
                (f"Schedule '{schedule}' is not in a recognised format! Reverting to default of '* * * * *'.")
            )
            return CronTrigger.from_crontab("* * * * *")

    def run(self):
        scheduler = BackgroundScheduler()
        schedule = self.schedule_fn()

        job = scheduler.add_job(self.tick, trigger=self._get_trigger(schedule))
        scheduler.start()

        try:
            while scheduler.running:
                new_schedule = self.schedule_fn()
                if new_schedule != schedule:
                    self.log.debug(f"Schedule has been changed from {schedule} to {new_schedule}! Rescheduling…")
                    schedule = new_schedule
                    job.reschedule(self._get_trigger(schedule))
                sleep(5)
        except KeyboardInterrupt:
            self.log.debug("Shutting down…")
            scheduler.shutdown()
            self.log.debug("Done!")

    def tick(self):
        try:
            self.callback()
        except Exception as e:
            if settings.DEBUG:
                raise
            else:
                self.log.error(e)
