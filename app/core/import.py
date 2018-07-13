from app.reporting import get_logger
from app.queues import import_queue


log = get_logger('ipdr')


class ImportDirector:
    def enter_loop(self):
        for transaction in import_queue.pull():
            log.info(f"Received transaction: {transaction}")
