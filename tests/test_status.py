from redis import StrictRedis
import pytest

from app.status import StatusMonitor, redis_args
import settings


@pytest.fixture
def redis():
    r = StrictRedis.from_url(settings.REDIS_DSN, **redis_args)
    yield r
    r.flushall()


def test_checkins(redis: StrictRedis):
    monitor = StatusMonitor(redis)

    class CheckinTest123:
        pass

    monitor.checkin(CheckinTest123())

    key, *others = [k.decode() for k in redis.keys()]
    assert len(others) == 0
    assert key == f"{settings.REDIS_KEY_PREFIX}:status:checkins:CheckinTest123"


def test_health_report(redis):
    monitor = StatusMonitor(redis)

    class HealthReportTest123:
        pass

    monitor.checkin(HealthReportTest123())

    report = monitor.report()

    assert len(report["checkins"]) == 1
    assert (
        report["checkins"][0]["key"]
        == f"{settings.REDIS_KEY_PREFIX}:status:checkins:HealthReportTest123"
    )
    assert report["checkins"][0]["name"] == "HealthReportTest123"
    assert {"postgres", "redis"}.issubset({s["name"] for s in report["services"]})


def test_health_report_without_redis():
    redis = StrictRedis(host="99.99.99.99", **redis_args)
    monitor = StatusMonitor(redis)
    report = monitor.report()

    assert report["checkins"] == []
    assert (
        next(s for s in report["services"] if s["name"] == "redis")["healthy"] is False
    )
