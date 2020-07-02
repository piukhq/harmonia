import typing as t
import socket
from redis.exceptions import WatchError
from logging import Logger
from time import sleep

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.reporting import get_logger
from app import db
import settings


def is_leader(lock_name: str, *, hostname=None):
    lock_key = f"{settings.REDIS_KEY_PREFIX}:schedule-lock:{lock_name}"
    if hostname is None:
        hostname = socket.gethostname()
    is_leader = False

    with db.redis.pipeline() as pipe:
        try:
            pipe.watch(lock_key)
            leader_host = pipe.get(lock_key)
            if leader_host in (hostname, None):
                pipe.multi()
                pipe.setex(lock_key, 10, hostname)
                pipe.execute()
                is_leader = True
        except WatchError:
            pass  # somebody else changed the key

    return is_leader


class CronScheduler:
    def __init__(self, *, name: str, schedule_fn: t.Callable, callback: t.Callable, logger: Logger = None):
        self.name = name
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
            if is_leader(self.name):
                self.callback()
        except Exception as e:
            if settings.DEBUG:
                raise
            else:
                self.log.error(e)
