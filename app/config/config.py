import typing as t

from app.config.models import ConfigItem
from app.db import get_or_create, redis, run_query, session_scope
from app.reporting import get_logger
import settings

log = get_logger("config")

KEY_PREFIX = f"{settings.REDIS_KEY_PREFIX}:config:"


class ConfigKeyError(Exception):
    pass


def _validate_key(key: str) -> None:
    if not key.startswith(KEY_PREFIX):
        raise ValueError(f"Config key must start with `{KEY_PREFIX}`")


def _set_default(key: str, val: str):
    with session_scope() as session:
        config_item, created = get_or_create(ConfigItem, session=session, defaults={"key": key, "value": val}, key=key)
        if not created and config_item.value != val:
            config_item.value = val
        redis.set(key, val, nx=True)


def _fetch_and_cache(key: str):
    val = None
    with session_scope() as session:
        config_item = run_query(
            lambda: session.query(ConfigItem).filter_by(key=key).one_or_none(),
            session=session,
            description=f"get {ConfigItem.__name__} object",
        )
        if config_item:
            val = t.cast(str, config_item.value)
            redis.set(key, val)
    return val


def get(key: str, *, default=None) -> t.Optional[str]:
    _validate_key(key)
    if default is not None:
        _set_default(key, default)

    val = t.cast(t.Optional[str], redis.get(key))
    if not val:
        val = _fetch_and_cache(key)
    return val


def update(key: str, value: str) -> None:
    _validate_key(key)
    with session_scope() as session:
        config_item = run_query(
            lambda: session.query(ConfigItem).filter_by(key=key).one_or_none(),
            session=session,
            description=f"get {ConfigItem.__name__} object",
        )
        if not config_item:
            raise ConfigKeyError(f"Can't update key `{key}` as it doesn't exist")

        config_item.value = value
        redis.set(key, value)


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
