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

    def scheduled_task_checkin(self, slug):
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

    def report(self):
        return {
            'checkins': [{
                'key': key.decode(),
                **self._get_checkin_details(key.decode())
            } for key in self.redis.scan_iter(f"{settings.REDIS_KEY_PREFIX}:status:checkins:*")]
        }


status_monitor = StatusMonitor(StrictRedis.from_url(settings.REDIS_DSN))
