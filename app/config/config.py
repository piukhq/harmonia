import contextlib
import typing as t

from sqlalchemy.orm.session import Session

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


def get(key: str, *, default: str = "", session: Session) -> t.Optional[str]:
    _validate_key(key)
    val = t.cast(t.Optional[str], redis.get(key))
    if val is None:
        config_item, _ = get_or_create(ConfigItem, key=key, defaults={"key": key, "value": default}, session=session)
        val = config_item.value
        redis.set(key, t.cast(str, val))
    return val


def update(key: str, value: str, *, session: Session) -> None:
    _validate_key(key)
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
    def __init__(self, key: str, *, default: str, session: Session = None) -> None:
        self.key = key
        self.default = default
        self.session = session

    def __get__(self, instance, owner):
        cm = contextlib.nullcontext(enter_result=self.session) if self.session else session_scope()
        with cm as session:
            return get(self.key, default=self.default, session=session)
