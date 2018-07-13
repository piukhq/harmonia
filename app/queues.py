from kombu import Connection, Exchange, Queue

from app.reporting import get_logger
from app import schemas
import settings


log = get_logger('msgq')


class QueueSchemaError(Exception):
    pass


class StrictQueue:
    def __init__(self, transport_dsn, *, name, schema_class, retry=True):
        self.connection = Connection(transport_dsn, connect_timeout=3)
        self.producer = self.connection.Producer()

        self.queue = Queue(name, Exchange(name), routing_key=name)

        self.schema = schema_class()

        self.retry = retry
        self.retry_policy = {
            'interval_start': 3,
            'interval_step': 3,
            'interval_max': 30,
            'errback': self.retry_error_callback,
        }

        self.connection.ensure_connection(**self.retry_policy)

    def retry_error_callback(self, exc, interval):
        log.warning(f"Failed to connect to RabbitMQ: {exc}. Retrying in {interval}s...")

    def push(self, obj, many=False):
        log.debug(f"Pushing {type(obj).__name__} to queue '{self.queue.name}', many: {many}")
        if many is True:
            for element in obj:
                self._produce(element)
        else:
            self._produce(obj)

    def _produce(self, obj):
        log.debug(f"Dumping {obj.__class__.__name__} object with {self.schema.__class__.__name__}")
        data, errors = self.schema.dump(obj)
        if errors:
            raise QueueSchemaError(errors)

        log.debug(f"Dumped data: {data}. Publishing...")
        self.producer.publish(
            data,
            retry=self.retry,
            retry_policy=self.retry_policy,
            exchange=self.queue.exchange,
            routing_key=self.queue.routing_key,
            declare=[self.queue])
        log.debug('Published!')


import_queue = StrictQueue(settings.QUEUE_TRANSPORT_DSN, name='imports', schema_class=schemas.SchemeTransactionSchema)
