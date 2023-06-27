import logging

from kombu import Producer, Queue

from app.data_warehouse.connector import queue_connection

log = logging.getLogger(__name__)

dead_letter_exchange = "tx_plutus_dl_exchange"
dead_letter_queue_name = "tx_plutus_dl_queue"
dw_queue_name = "tx_export_dw"

dw_queue = Queue(
    dw_queue_name,
    queue_arguments={
        "x-dead-letter-routing-key": dead_letter_queue_name,
        "x-dead-letter-exchange": dead_letter_exchange,
    },
)


def _on_error(exc, interval):
    log.warning(f"Failed to connect to RabbitMQ: {exc}. Will retry after {interval:.1f}s...")


def add(message: dict) -> None:
    channel = queue_connection().channel()
    producer = Producer(channel=channel, routing_key=dw_queue_name)
    producer.publish(message)
