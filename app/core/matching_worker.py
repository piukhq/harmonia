import time

from app.reporting import get_logger
from app.status import status_monitor
from app.queues import matching_queue


log = get_logger('mchw')


class MatchingWorker:
    def __init__(self, name: str) -> None:
        self.name = name

    def enter_loop(self) -> None:
        def handle_transaction(transaction):
            status_monitor.checkin(f"{type(self).__name__}:{self.name}")
            log.info(f"I would match this! {transaction}")
            log.info("sleeping for a while to pretend i'm super busy...")
            time.sleep(10)
            log.info("all done!")

        matching_queue.pull(handle_transaction)
