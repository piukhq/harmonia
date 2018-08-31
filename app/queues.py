import typing as t
import logging

from kombu import Connection, Exchange, Queue, Message
from kombu.mixins import ConsumerMixin
from marshmallow.exceptions import ValidationError

from app.reporting import get_logger
from app import schemas
import settings

amqp_logger = logging.getLogger('amqp')
amqp_logger.setLevel(logging.INFO)

log = get_logger('msgq')


class QueuePushSchemaError(Exception):
    pass


class QueuePullSchemaError(Exception):
    pass


class StrictQueue:
    def __init__(self, transport_dsn: str, *, name: str, schema_class, retry: bool = True) -> None:
        self.connection = Connection(transport_dsn, connect_timeout=3, heartbeat=5)
        self.queue = Queue(name, Exchange(name), routing_key=name)
        self.producer = self.connection.Producer()

        self.schema = schema_class()

        self.retry = retry
        self.retry_policy = {
            'interval_start': 3,
            'interval_step': 3,
            'interval_max': 30,
            'errback': self._retry_callback,
        }

        self.connection.ensure_connection(**self.retry_policy)

    def _retry_callback(self, exc: Exception, interval: float) -> None:
        log.warning(f"Failed to connect to RabbitMQ @ {self.connection.hostname}: {exc}. Retrying in {interval}s...")

    def _produce(self, obj: t.Dict) -> None:
        data = self.schema.dump(obj)

        errors = self.schema.validate(data)
        if errors:
            raise QueuePushSchemaError(errors)

        log.debug(f"Dumped data: {data}. Publishing now.")
        self.producer.publish(
            data,
            retry=self.retry,
            retry_policy=self.retry_policy,
            exchange=self.queue.exchange,
            routing_key=self.queue.routing_key,
            declare=[self.queue])

    def push(self, obj: t.Dict, many: bool = False) -> None:
        log.debug(f"Pushing {type(obj).__name__} to queue '{self.queue.name}', many: {many}.")
        if many is True:
            for element in obj:
                self._produce(element)
        else:
            self._produce(obj)

    def pull(self, message_callback: t.Callable):
        class Worker(ConsumerMixin):
            def __init__(self, connection: Connection, queue: Queue, *, message_callback: t.Callable) -> None:
                self.connection = connection
                self.queue = queue
                self.message_callback = message_callback

            def get_consumers(self, consumer_class: t.Type, channel) -> t.List:
                return [consumer_class(queues=[self.queue], callbacks=[self.message_callback])]

            def on_connection_error(self, exc: Exception, interval: float) -> None:
                log.warning(f"Lost connection to broker ({exc}), will retry in {interval}s.")

            def on_connection_revived(self) -> None:
                log.info(f"Revived connection to broker.")

        def receive_message(body: t.Dict, message: Message) -> None:
            try:
                obj = self.schema.load(body)
            except ValidationError as ex:
                raise QueuePullSchemaError(ex.messages)

            try:
                message_callback(obj)
            except Exception as ex:
                log.error(
                    f"Message handler '{message_callback.__name__}' on the '{self.queue.name}' queue has failed ({ex})."
                    ' Message has not been acknowledged.')
            else:
                message.ack()

        worker = Worker(self.connection, self.queue, message_callback=receive_message)
        worker.run()


matching_queue = StrictQueue(settings.AMQP_DSN, name='matching', schema_class=schemas.SchemeTransactionSchema)
