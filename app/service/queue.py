import logging

from kombu import Connection

import settings

log = logging.getLogger(__name__)


def _on_error(exc, interval):
    log.warning(f"Failed to connect to RabbitMQ: {exc}. Will retry after {interval:.1f}s...")


def add(message: dict, *, provider: str, queue_name: str) -> None:
    with Connection(settings.RABBITMQ_DSN, connect_timeout=3) as conn:
        conn.ensure_connection(
            errback=_on_error, max_retries=3, interval_start=0.2, interval_step=0.4, interval_max=1, timeout=3
        )
        q = conn.SimpleQueue(queue_name)
        q.put(message, headers={"X-Provider": provider})
