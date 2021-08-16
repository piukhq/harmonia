import pytest
from redis import Redis

import settings
from app.status import StatusMonitor


@pytest.fixture
def redis():
    from app.db import redis

    redis.flushall()

    yield redis
    redis.flushall()


def test_checkins(redis: Redis):
    monitor = StatusMonitor()

    class CheckinTest123:
        pass

    monitor.checkin(CheckinTest123())

    key, *others = redis.keys()
    assert len(others) == 0
    assert key == f"{settings.REDIS_KEY_PREFIX}:status:checkins:CheckinTest123"


def test_health_report(redis: Redis):
    monitor = StatusMonitor()

    class HealthReportTest123:
        pass

    monitor.checkin(HealthReportTest123())

    report = monitor.report()

    assert len(report["checkins"]) == 1
    assert report["checkins"][0]["key"] == f"{settings.REDIS_KEY_PREFIX}:status:checkins:HealthReportTest123"
    assert report["checkins"][0]["name"] == "HealthReportTest123"
    assert {"postgres", "redis"}.issubset({s["name"] for s in report["services"]})
