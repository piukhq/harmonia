from collections import namedtuple

from app import queues, schemas
import settings


Feed = namedtuple('Feed', 'queue')

scheme = Feed(
    queue=queues.StrictQueue(
        settings.AMQP_DSN,
        name='imports-scheme',
        schema_class=schemas.SchemeTransactionSchema))

payment = Feed(
    queue=queues.StrictQueue(
        settings.AMQP_DSN,
        name='imports-payment',
        schema_class=schemas.PaymentTransactionSchema))
