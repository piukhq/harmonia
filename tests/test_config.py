from uuid import uuid4

from redis import StrictRedis
import pytest

from app import config
import settings


@pytest.fixture
def accessor():
    redis = StrictRedis.from_url(settings.TEST_REDIS_DSN)
    yield config.ConfigAccessor(redis=redis)
    redis.flushdb()


def test_get_non_existent_config_value(accessor):
    v = str(uuid4())
    assert accessor.get('test.key', default=v) == v


def test_get_existent_config_value(accessor):
    v = str(uuid4())
    accessor.redis.set('test.key', v)
    assert accessor.get('test.key') == v


def test_get_existent_config_value_with_default(accessor):
    v = str(uuid4())
    accessor.redis.set('test.key', v)
    assert accessor.get('test.key', default=str(uuid4())) == v
