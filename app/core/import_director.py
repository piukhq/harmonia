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
    def handle_scheme_tx(self, scheme_tx):
        status_monitor.checkin(self)

        session.add(scheme_tx)
        session.commit()

        log.info(f"Received & persisted scheme transaction {scheme_tx.transaction_id}! Posting to the matching queue.")
        queues.matching_queue.push(scheme_tx)

    def enter_loop(self) -> None:
        feeds.scheme.queue.pull(self.handle_scheme_tx)


class PaymentImportDirector(ImportDirector):
    def handle_payment_tx(self, payment_tx):
        status_monitor.checkin(self)

        session.add(payment_tx)
        session.commit()

        log.info(f"Received & persisted payment transaction {payment_tx.transaction_id}!")

    def enter_loop(self) -> None:
        feeds.payment.queue.pull(self.handle_payment_tx)
