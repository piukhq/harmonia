import typing as t

from app.reporting import get_logger
from app.db import redis
import settings

log = get_logger("config")

KEY_PREFIX = f"{settings.REDIS_KEY_PREFIX}:config:"


def _validate_key(key: str) -> None:
    if not key.startswith(KEY_PREFIX):
        raise ValueError(f"Config key must start with `{KEY_PREFIX}`")


def get(key: str, *, default=None) -> t.Optional[str]:
    _validate_key(key)
    if default is not None:
        redis.set(key, default, nx=True)
    val = t.cast(t.Optional[str], redis.get(key))
    return val


def update(key: str, value: str) -> None:
    _validate_key(key)
    if redis.set(key, value, xx=True) is None:
        raise KeyError(f"Can't update key `{key}` as it doesn't exist")


def all_keys() -> t.Iterable[t.Tuple[str, t.Optional[str]]]:
    for key in redis.scan_iter(f"{KEY_PREFIX}*"):
        val = t.cast(t.Optional[str], redis.get(key))
        yield (key, val)


class ConfigValue:
    def __init__(self, key: str, default: str = None) -> None:
        self.key = key
        self.default = default

    def __get__(self, instance, owner):
        return get(self.key, default=self.default)
