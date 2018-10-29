from collections import namedtuple

from redis import StrictRedis

import settings
from app.reporting import get_logger

log = get_logger('matching-retry')

KEY_PREFIX = f"{settings.REDIS_KEY_PREFIX}:matching-retry:"

_redis = StrictRedis.from_url(settings.REDIS_DSN)

RetryEntry = namedtuple('RetryEntry', 'retry_at retry_count queued_at')


def store(payment_transaction_id: int, retry_entry: RetryEntry) -> None:
    log.debug(f"Storing retry {retry_entry} for payment transaction #{payment_transaction_id}")
    _redis.hmset(f"{KEY_PREFIX}{payment_transaction_id}", retry_entry._asdict())


def get(payment_transaction_id: int) -> RetryEntry:
    log.debug(f"Retrieving retry for payment transaction #{payment_transaction_id}")
    entry = _redis.hgetall(f"{KEY_PREFIX}{payment_transaction_id}")
    if entry is None:
        raise KeyError
    return RetryEntry(**{k.decode(): int(v.decode()) for k, v in entry.items()})


def all():
    for key in _redis.scan_iter(f"{KEY_PREFIX}*"):
        payment_tx_id = int(key[len(KEY_PREFIX):])
        yield payment_tx_id, get(payment_tx_id)


def clear(payment_transaction_id: int) -> None:
    log.debug(f"Clearing retries for payment transaction #{payment_transaction_id}")
    _redis.delete(f"{KEY_PREFIX}{payment_transaction_id}")
