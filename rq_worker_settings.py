import settings

QUEUES = [name for name in settings.getenv("TXM_RQ_QUEUES", default="").split(",") if name]
