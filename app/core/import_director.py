from app.reporting import get_logger
from app.queues import import_queue


log = get_logger('ipdr')


class ImportDirector:
    def enter_loop(self):
        def handle_transaction(transaction):
            log.info(f"Received {transaction}! This would be imported, matched, et cetera.")
        import_queue.pull(handle_transaction)
