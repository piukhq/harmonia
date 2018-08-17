from datetime import datetime
import time
import re

from redis import StrictRedis
import humanize

import settings


class StatusMonitor:
    checkin_name_pattern = re.compile(f"{settings.REDIS_KEY_PREFIX}:status:checkins:(.*)")

    def __init__(self, redis):
        self.redis = redis

    def checkin(self, slug):
        key = f"{settings.REDIS_KEY_PREFIX}:status:checkins:{slug}"
        self.redis.set(key, time.time())

    def _get_checkin_details(self, key):
        checkin_timestamp = float(self.redis.get(key).decode())
        checkin_datetime = datetime.fromtimestamp(checkin_timestamp)
        seconds_ago = time.time() - checkin_timestamp
        checkin_name = self.checkin_name_pattern.match(key).group(1)
        return {
            'timestamp': checkin_timestamp,
            'datetime': checkin_datetime,
            'seconds_ago': seconds_ago,
            'human_readable': humanize.naturaltime(checkin_datetime),
            'name': checkin_name,
        }

    def _get_postgres_health(self):
        from psycopg2 import connect

        errors = []
        try:
            with connect(settings.POSTGRES_DSN) as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT 1')
                    cur.fetchone()
                    healthy = True
        except Exception as ex:
            healthy = False
            errors.append(ex)

        return {
            'dsn': settings.POSTGRES_DSN,
            'healthy': healthy,
            'errors': errors,
        }

    def _get_redis_health(self):
        from redis import StrictRedis

        errors = []
        try:
            r = StrictRedis.from_url(settings.REDIS_DSN)
            r.ping()
            healthy = True
        except Exception as ex:
            healthy = False
            errors.append(ex)

        return {
            'dsn': settings.REDIS_DSN,
            'healthy': healthy,
            'errors': errors,
        }

    def _get_amqp_health(self):
        from kombu import Connection

        errors = []
        try:
            conn = Connection(settings.AMQP_DSN, connect_timeout=3, heartbeat=5)
            conn.connect()
            healthy = True
        except Exception as ex:
            healthy = False
            errors.append(ex)

        return {
            'dsn': settings.AMQP_DSN,
            'healthy': healthy,
            'errors': errors,
        }

    def report(self):
        redis_health = self._get_redis_health()

        if redis_health['healthy']:
            checkins = [{
                'key': key.decode(),
                **self._get_checkin_details(key.decode())
            } for key in self.redis.scan_iter(f"{settings.REDIS_KEY_PREFIX}:status:checkins:*")]
        else:
            checkins = []

        return {
            'checkins': checkins,
            'services': [{
                'name': 'postgres',
                **self._get_postgres_health(),
            }, {
                'name': 'redis',
                **redis_health,
            }, {
                'name': 'amqp',
                **self._get_amqp_health(),
            }],
        }


status_monitor = StatusMonitor(StrictRedis.from_url(settings.REDIS_DSN))
