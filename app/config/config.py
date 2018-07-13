from redis import StrictRedis

from app.reporting import get_logger
import settings


log = get_logger('conf')

KEY_PREFIX = f"{settings.REDIS_KEY_PREFIX}:config:"


_redis = StrictRedis.from_url(settings.REDIS_DSN)


def _validate_key(key):
    if not key.startswith(KEY_PREFIX):
        raise ValueError(f"Config key must start with `{KEY_PREFIX}`.")


def get(key, *, default=None, redis=_redis):
    _validate_key(key)
    redis.set(key, default, nx=True)
    val = redis.get(key)
    return val.decode() if val is not None else None


def update(key, value, *, redis=_redis):
    _validate_key(key)
    if redis.set(key, value, xx=True) is None:
        raise KeyError(f"Can't update key `{key}` as it doesn't exist!")


def all_keys(*, redis=_redis):
    for key in redis.scan_iter(f"{KEY_PREFIX}*"):
        yield (key.decode(), redis.get(key).decode())


class ConfigValue:
    def __init__(self, key, default=None):
        self.key = key
        self.default = default

    def __get__(self, instance, owner, redis=_redis):
        return get(self.key, default=self.default, redis=redis)
