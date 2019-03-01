import time
import re

from redis import StrictRedis
import humanize
import pendulum

from app.reporting import get_logger
import settings


log = get_logger("status-monitor")


class StatusMonitor:
    checkin_name_pattern = re.compile(f"{settings.REDIS_KEY_PREFIX}:status:checkins:(.*)")

    def __init__(self, redis: StrictRedis) -> None:
        self.redis = redis

    def checkin(self, obj: object, suffix: str = None) -> None:
        if suffix is not None:
            checkin_name = f"{type(obj).__name__}:{suffix}"
        else:
            checkin_name = type(obj).__name__

        key = f"{settings.REDIS_KEY_PREFIX}:status:checkins:{checkin_name}"
        self.redis.set(key, time.time())
        log.debug(f"Service {checkin_name} has checked in.")

    def _get_checkin_details(self, key: str) -> dict:
        checkin_timestamp = float(self.redis.get(key).decode())
        checkin_datetime = pendulum.from_timestamp(checkin_timestamp)
        seconds_ago = time.time() - checkin_timestamp

        checkin_name_match = self.checkin_name_pattern.match(key)
        if checkin_name_match is not None:
            checkin_name = checkin_name_match.group(1)
        else:
            checkin_name = f"<failed to get name from key {repr(key)}>"

        return {
            "timestamp": checkin_timestamp,
            "datetime": checkin_datetime,
            "seconds_ago": seconds_ago,
            "human_readable": humanize.naturaltime(checkin_datetime.naive()),  # humanize uses naive datetimes
            "name": checkin_name,
        }

    def _get_postgres_health(self) -> dict:
        from psycopg2 import connect

        errors = []
        try:
            with connect(settings.POSTGRES_DSN) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
                    healthy = True
        except Exception as ex:
            healthy = False
            errors.append(ex)

        return {"dsn": settings.POSTGRES_DSN, "healthy": healthy, "errors": errors}

    def _get_redis_health(self) -> dict:
        errors = []
        try:
            self.redis.ping()
            healthy = True
        except Exception as ex:
            healthy = False
            errors.append(ex)

        return {"dsn": settings.REDIS_DSN, "healthy": healthy, "errors": errors}

    def report(self) -> dict:
        redis_health = self._get_redis_health()

        if redis_health["healthy"]:
            checkins = [
                {"key": key.decode(), **self._get_checkin_details(key.decode())}
                for key in self.redis.scan_iter(f"{settings.REDIS_KEY_PREFIX}:status:checkins:*")
            ]
        else:
            checkins = []

        return {
            "checkins": checkins,
            "services": [{"name": "postgres", **self._get_postgres_health()}, {"name": "redis", **redis_health}],
        }


redis_args = {"socket_timeout": 1, "socket_connect_timeout": 3, "socket_keepalive": True, "retry_on_timeout": False}
status_monitor = StatusMonitor(StrictRedis.from_url(settings.REDIS_DSN, **redis_args))
