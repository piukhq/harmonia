from kombu import Connection

import settings

_connection = None


def queue_connection():
    global _connection
    if not _connection:
        _connection = Connection(settings.RABBITMQ_DSN, connect_timeout=3, heartbeat=1)
    return _connection
