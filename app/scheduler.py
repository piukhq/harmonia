import typing as t
from logging import Logger
from time import sleep

import sentry_sdk
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.util import undefined

from app.reporting import get_logger
import settings


class CronScheduler:
    default_schedule = "* * * * *"

    def __init__(
        self,
        *,
        schedule_fn: t.Callable,
        callback: t.Callable,
        coalesce_jobs: t.Optional[bool] = None,
        logger: Logger = None,
    ):
        self.schedule_fn = schedule_fn
        self.callback = callback
        self.coalesce_jobs = coalesce_jobs if coalesce_jobs is not None else undefined
        self.log = logger if logger is not None else get_logger("cron-scheduler")

    def __str__(self) -> str:
        return f"{self.__class__.__name__} with schedule '{self.schedule_fn()}'"

    def _get_trigger(self, schedule):
        try:
            return CronTrigger.from_crontab(schedule)
        except ValueError:
            self.log.error(
                (
                    f"Schedule '{schedule}' is not in a recognised format! "
                    f"Reverting to default of '{self.default_schedule}'."
                )
            )
            return CronTrigger.from_crontab(self.default_schedule)

    def run(self):
        scheduler = BackgroundScheduler()
        schedule = self.schedule_fn()
        if not schedule:
            self.log.warn((f"No schedule provided! Reverting to default of '{self.default_schedule}'."))
            schedule = self.default_schedule

        job = scheduler.add_job(self.tick, trigger=self._get_trigger(schedule), coalesce=self.coalesce_jobs)
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
        except Exception:
            if settings.DEBUG:
                raise
            else:
                sentry_sdk.capture_exception()
