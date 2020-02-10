import settings

REDIS_HOST = settings.REDIS_HOST
REDIS_PORT = settings.REDIS_PORT
REDIS_DB = settings.REDIS_DB
REDIS_PASSWORD = settings.REDIS_PASS

QUEUES = settings.getenv("TXM_RQ_QUEUES", default="").split(",")
