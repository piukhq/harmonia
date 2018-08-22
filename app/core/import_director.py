from app.reporting import get_logger
from app.queues import import_queue, matching_queue
from app.status import status_monitor
from app.db import Session

log = get_logger('ipdr')
session = Session()


class ImportDirector:
    def enter_loop(self):
        def handle_transaction(transaction):
            status_monitor.checkin(self.__class__.__name__)

            session.add(transaction)
            session.commit()

            log.info(f"Received & persisted transaction {transaction.transaction_id}! Posting to the matching queue.")
            matching_queue.push(transaction)

        import_queue.pull(handle_transaction)
