import typing as t

from redis.exceptions import RedisError
from sqlalchemy.orm.session import Session

import settings
from app.config import models
from app.db import get_or_create, redis, redis_scan, run_query
from app.reporting import get_logger

log = get_logger("config")

KEY_PREFIX = f"{settings.REDIS_KEY_PREFIX}:config:"


class ConfigKeyError(Exception):
    pass


def _validate_key(key: str) -> None:
    if not key.startswith(KEY_PREFIX):
        raise ValueError(f"Config key must start with `{KEY_PREFIX}`")


def get(key: str, *, default: str = "", session: Session) -> str:
    _validate_key(key)
    try:
        val = t.cast(t.Optional[str], redis.get(key))
    except RedisError as ex:
        log.warning(f"Error getting key {key} from redis: '{ex}'. Trying the database...")
        config_item = run_query(
            lambda: session.query(models.ConfigItem).filter_by(key=key).one_or_none(),
            session=session,
            description=f"get {models.ConfigItem.__name__} object",
        )
        val = config_item.value if config_item else None

    if val is None:
        config_item, _ = get_or_create(
            models.ConfigItem, key=key, defaults={"key": key, "value": default}, session=session
        )
        val = config_item.value
        try:
            redis.set(key, t.cast(str, val))
        except RedisError as ex:
            log.warning(f"Error setting key {key} in redis: {ex}")

    return val


def update(key: str, value: str, *, session: Session) -> None:
    _validate_key(key)
    config_item = run_query(
        lambda: session.query(models.ConfigItem).filter_by(key=key).one_or_none(),
        session=session,
        description=f"get {models.ConfigItem.__name__} object",
    )
    if not config_item:
        raise ConfigKeyError(f"Can't update key `{key}` as it doesn't exist")

    config_item.value = value
    redis.set(key, value)


def all_keys() -> t.Iterable[t.Tuple[str, t.Optional[str]]]:
    for key in redis_scan(f"{KEY_PREFIX}*"):
        val = t.cast(t.Optional[str], redis.get(key))
        yield (key, val)


class ConfigValue(t.NamedTuple):
    name: str
    key: str
    default: str


class ConfigError(Exception):
    pass


class Config:
    def __init__(self, *args: ConfigValue):
        self._name_val_map = {arg.name: arg for arg in args}

    def get(self, name: str, session: Session) -> str:
        config_value = self._name_val_map.get(name)
        if config_value is None:
            raise ConfigError(f"{Config.__name__} contains no {ConfigValue.__name__} with name {name}.")
        return get(config_value.key, default=config_value.default, session=session)
