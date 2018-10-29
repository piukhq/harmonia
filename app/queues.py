import logging
import typing as t

import pendulum
from kombu import Connection, Exchange, Message, Queue
from kombu.mixins import ConsumerMixin
from marshmallow.exceptions import ValidationError

import settings
from app import schemas
from app.reporting import get_logger

amqp_logger = logging.getLogger('amqp')
amqp_logger.setLevel(logging.INFO)


class QueuePushSchemaError(Exception):
    pass


class QueuePullSchemaError(Exception):
    pass


class StrictQueue:
    def __init__(self, transport_dsn: str, *, name: str, schema_class, retry: bool = True) -> None:
        self.connection = Connection(transport_dsn, connect_timeout=3)
        self.queue = Queue(name, Exchange(name), routing_key=name)
        self.producer = self.connection.Producer(serializer=settings.JSON_SERIALIZER)

        self.schema = schema_class()

        self.retry = retry
        self.retry_policy = {
            'interval_start': 3,
            'interval_step': 3,
            'interval_max': 30,
            'errback': self._retry_callback,
        }

        self.log = get_logger(f"message-queue.{name}")

        # note: we may not need to try connecting so early.
        # i've commented it out for now to see if any connection issues arise.
        # self.connection.ensure_connection(**self.retry_policy)

    def _retry_callback(self, exc: Exception, interval: float) -> None:
        self.log.warning(f"Failed to connect to RabbitMQ @ {self.connection.hostname}: {exc}. Retrying in {interval}s…")

    def _get_headers(self, override_headers: t.Optional[dict]) -> dict:
        headers = {
            'X-Queued-At': pendulum.now().int_timestamp,
            'X-Retry-Count': 0,
        }

        if override_headers is not None:
            headers.update(override_headers)

        return headers

    def _produce(self, obj: dict, override_headers: t.Optional[dict]) -> None:
        data = self.schema.dump(obj)
        headers = self._get_headers(override_headers)

        errors = self.schema.validate(data)
        if errors:
            raise QueuePushSchemaError(errors)

        self.connection.ensure_connection(**self.retry_policy)

        self.log.debug(f"Dumped data: {data}. Publishing now.")

        self.producer.publish(
            data,
            retry=self.retry,
            retry_policy=self.retry_policy,
            exchange=self.queue.exchange,
            routing_key=self.queue.routing_key,
            declare=[self.queue],
            headers=headers)

    def push(self, obj: t.Union[dict, list], *, many: bool = False, override_headers: dict = None) -> None:
        self.log.debug(f"Pushing {type(obj).__name__} to queue '{self.queue.name}', many: {many}.")
        if isinstance(obj, list):
            assert many is True
            for element in obj:
                self._produce(element, override_headers)
        else:
            self._produce(obj, override_headers)

    def pull(self, message_callback: t.Callable, raise_exceptions: bool = False, once: bool = False):
        """Start consuming messages from the queue. The consumer cleanly handles connection issues.

        message_callback is called for each message that is called. It is expected to accept two parameters:
        * the deserialized object from the queue message
        * a dictionary of message headers (e.g. retry count, queue time, et cetera)

        message_callback is expected to return a boolean value indicated whether the message should be acknowledged.
        If message_callback returns anything other than False (including None), the message will be acknowledged.
        However, it is good practice to explicitly return True.

        If raise_exceptions is set, any exception raised in message_callback will not be handled."""

        class Worker(ConsumerMixin):
            def __init__(self, connection: Connection, queue: Queue, *, message_callback: t.Callable,
                         parent: StrictQueue, once: bool) -> None:
                self.connection = connection
                self.queue = queue
                self.message_callback = message_callback
                self.parent = parent
                self.once = once

            def get_consumers(self, consumer_class: t.Type, channel) -> list:
                return [consumer_class(queues=[self.queue], callbacks=[self.message_callback])]

            def on_connection_error(self, exc: Exception, interval: float) -> None:
                self.parent.log.warning(f"Lost connection to broker ({exc}), will retry in {interval}s.")

            def on_connection_revived(self) -> None:
                self.parent.log.info('Revived connection to broker.')

            def on_iteration(self) -> None:
                if self.once is True:
                    self.parent.log.warning('Shutting down because "once" flag is set')
                    self.should_stop = True

        def receive_message(body: dict, message: Message) -> None:
            try:
                obj = self.schema.load(body)
            except ValidationError as ex:
                raise QueuePullSchemaError(ex.messages)

            try:
                acknowledge = message_callback(obj, message.headers)
            except Exception as ex:
                if raise_exceptions is True:
                    raise
                else:
                    self.log.error(f"Message handler '{message_callback.__name__}' on the '{self.queue.name}' queue "
                                   f"has failed ({ex}). Message has not been acknowledged.")
            else:
                if acknowledge is not False:
                    message.ack()

        worker = Worker(self.connection, self.queue, message_callback=receive_message, parent=self, once=once)
        worker.run()


matching_queue = StrictQueue(settings.AMQP_DSN, name='matching', schema_class=schemas.MatchingQueueSchema)
export_queue = StrictQueue(settings.AMQP_DSN, name='export', schema_class=schemas.ExportQueueSchema)
scheme_import_queue = StrictQueue(
    settings.AMQP_DSN, name='imports-scheme', schema_class=schemas.SchemeImportQueueSchema)
payment_import_queue = StrictQueue(
    settings.AMQP_DSN, name='imports-payment', schema_class=schemas.PaymentImportQueueSchema)
