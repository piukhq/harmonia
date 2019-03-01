import settings

REDIS_URL = settings.REDIS_DSN
QUEUES = settings.getenv("TXM_RQ_QUEUES").split(",")
SENTRY_DSN = settings.SENTRY_DSN
