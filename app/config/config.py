import typing as t

from redis import StrictRedis
import tenacity

from app.reporting import get_logger
import settings

log = get_logger("config")

KEY_PREFIX = f"{settings.REDIS_KEY_PREFIX}:config:"

_redis = StrictRedis.from_url(settings.REDIS_DSN)


def _retry_callback(retry_state: tenacity.RetryCallState) -> None:
    wait = _ensure_connection.retry.wait
    sleep_for = min(
        wait.max, wait.start + (retry_state.attempt_number - 1) * wait.increment
    )

    log.error(
        f'Failed to connect to redis: "{retry_state.outcome.exception()}". '
        f"Retrying in {sleep_for}s…"
    )


@tenacity.retry(
    wait=tenacity.wait_incrementing(start=3, increment=3, max=30),
    before_sleep=_retry_callback,
)
def _ensure_connection(redis: StrictRedis) -> None:
    redis.ping()


def _validate_key(key: str) -> None:
    if not key.startswith(KEY_PREFIX):
        raise ValueError(f"Config key must start with `{KEY_PREFIX}`")


def get(key: str, *, default=None, redis: StrictRedis = _redis) -> str:
    _validate_key(key)
    _ensure_connection(redis)
    if default is not None:
        redis.set(key, default, nx=True)
    val = redis.get(key)
    return val.decode() if val is not None else None


def update(key: str, value: str, *, redis: StrictRedis = _redis) -> None:
    _validate_key(key)
    _ensure_connection(redis)
    if redis.set(key, value, xx=True) is None:
        raise KeyError(f"Can't update key `{key}` as it doesn't exist")


def all_keys(*, redis: StrictRedis = _redis) -> t.Iterable[t.Tuple[str, str]]:
    _ensure_connection(redis)
    for key in redis.scan_iter(f"{KEY_PREFIX}*"):
        yield (key.decode(), redis.get(key).decode())


class ConfigValue:
    def __init__(self, key: str, default: str = None) -> None:
        self.key = key
        self.default = default

    def __get__(self, instance, owner, redis: StrictRedis = _redis):
        return get(self.key, default=self.default, redis=redis)
