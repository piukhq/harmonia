import logging

from kombu import Connection, Exchange, Queue
from kombu.mixins import ConsumerMixin

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
    def __init__(self, transport_dsn, *, name, schema_class, retry=True):
        self.connection = Connection(
            transport_dsn,
            connect_timeout=3,
            heartbeat=5)

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

    def _retry_callback(self, exc, interval):
        log.warning(f"Failed to connect to RabbitMQ: {exc}. Retrying in {interval}s...")

    def _produce(self, obj):
        log.debug(f"Dumping {obj.__class__.__name__} object with {self.schema.__class__.__name__}")
        data, errors = self.schema.dump(obj)
        if errors:
            raise QueuePushSchemaError(errors)

        log.debug(f"Dumped data: {data}. Publishing...")
        self.producer.publish(
            data,
            retry=self.retry,
            retry_policy=self.retry_policy,
            exchange=self.queue.exchange,
            routing_key=self.queue.routing_key,
            declare=[self.queue])
        log.debug('Published!')

    def push(self, obj, many=False):
        log.debug(f"Pushing {type(obj).__name__} to queue '{self.queue.name}', many: {many}")
        if many is True:
            for element in obj:
                self._produce(element)
        else:
            self._produce(obj)

    def pull(self, message_callback):
        class Worker(ConsumerMixin):
            def __init__(self, connection, queue, *, message_callback):
                self.connection = connection
                self.queue = queue
                self.message_callback = message_callback

            def get_consumers(self, consumer_class, channel):
                return [consumer_class(queues=[self.queue], callbacks=[self.message_callback])]

            def on_connection_error(self, exc, interval):
                log.warning(f"Lost connection to broker ({exc}), will retry in {interval}s.")

            def on_connection_revived(self):
                log.info(f"Revived connection to broker.")

        def receive_message(body, message):
            obj, errors = self.schema.load(body)
            if errors:
                raise QueuePullSchemaError(errors)

            try:
                message_callback(obj)
            except Exception as ex:
                log.error(
                    f"Message handler '{message_callback.__name__}' on the '{self.queue.name}' queue has failed ({ex})."
                    ' Message has not been acknowledged.')
            else:
                log.debug(
                    f"Message has been successfully processed by '{message_callback.__name__}' "
                    f"on the '{self.queue.name}' queue.")
                message.ack()

        worker = Worker(self.connection, self.queue, message_callback=receive_message)

        worker.run()


import_queue = StrictQueue(settings.QUEUE_TRANSPORT_DSN, name='imports', schema_class=schemas.SchemeTransactionSchema)
