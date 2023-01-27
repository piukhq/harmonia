import logging

from kombu import Connection, Exchange, Queue

import settings

log = logging.getLogger(__name__)

exchange = Exchange("tx_audit_exchange", type="fanout", durable=False)
atlas_queue = Queue("tx_matching", exchange=exchange)
plutus_queue = Queue("tx_plutus_dw", exchange=exchange)


def _on_error(exc, interval):
    log.warning(f"Failed to connect to RabbitMQ: {exc}. Will retry after {interval:.1f}s...")


def publish(message: dict, *, provider: str) -> None:
    with Connection(settings.RABBITMQ_DSN, connect_timeout=3) as conn:
        conn.ensure_connection(
            errback=_on_error, max_retries=3, interval_start=0.2, interval_step=0.4, interval_max=1, timeout=3
        )
        producer = conn.Producer(serializer="json")
        producer.publish(
            message, exchange=exchange, headers={"X-Provider": provider}, declare=[atlas_queue, plutus_queue]
        )
