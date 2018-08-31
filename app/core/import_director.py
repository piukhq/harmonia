from app.reporting import get_logger
from app import feeds, queues
from app.status import status_monitor
from app.db import Session

log = get_logger('ipdr')
session = Session()


class ImportDirector:
    def enter_loop(self) -> None:
        raise NotImplementedError


class SchemeImportDirector(ImportDirector):
    def enter_loop(self) -> None:
        def handle_scheme_tx(scheme_tx):
            status_monitor.checkin(self)

            session.add(scheme_tx)
            session.commit()

            log.info(
                f"Received & persisted scheme transaction {scheme_tx.transaction_id}! Posting to the matching queue.")
            queues.matching_queue.push(scheme_tx)

        feeds.scheme.queue.pull(handle_scheme_tx)


class PaymentImportDirector(ImportDirector):
    def enter_loop(self) -> None:
        def handle_payment_tx(payment_tx):
            status_monitor.checkin(self)

            session.add(payment_tx)
            session.commit()

            log.info(f"Received & persisted payment transaction {payment_tx.transaction_id}!")

        feeds.payment.queue.pull(handle_payment_tx)
