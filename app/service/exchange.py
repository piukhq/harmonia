import logging

from kombu import Connection, Exchange, Queue

import settings

log = logging.getLogger(__name__)

exchange = Exchange("tx_export_exchange", type="direct", durable=False)
atlas_queue = Queue("tx_matching", exchange=exchange, routing_key="atlas")
plutus_queue = Queue("tx_plutus_dw", exchange=exchange, routing_key="dw")


def _on_error(exc, interval):
    log.warning(f"Failed to connect to RabbitMQ: {exc}. Will retry after {interval:.1f}s...")


def publish(message: dict, *, provider: str, destination="all") -> None:
    with Connection(settings.RABBITMQ_DSN, connect_timeout=3) as conn:
        conn.ensure_connection(
            errback=_on_error, max_retries=3, interval_start=0.2, interval_step=0.4, interval_max=1, timeout=3
        )
        producer = conn.Producer(serializer="json")
        # Always send a message to Atlas
        producer.publish(
            message, exchange=exchange, headers={"X-Provider": provider}, declare=[atlas_queue], routing_key="atlas"
        )

        # Almost always send a message to the data warehouse, except where a message destination is only for atlas
        if destination == "all":
            producer.publish(
                message, exchange=exchange, headers={"X-Provider": provider}, declare=[plutus_queue], routing_key="dw"
            )
