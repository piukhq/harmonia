from app.reporting import get_logger
from app import queues
from app.status import status_monitor
from app.db import Session

log = get_logger("import-director")
session = Session()


class ImportDirector:
    def enter_loop(self, once: bool = False, debug: bool = False) -> None:
        raise NotImplementedError


class SchemeImportDirector(ImportDirector):
    def handle_scheme_tx(self, scheme_tx, headers):
        status_monitor.checkin(self)

        session.add(scheme_tx)
        session.commit()

        log.info(
            f"Received and persisted scheme transaction: {scheme_tx.transaction_id}."
        )

    def enter_loop(self, once: bool = False, debug: bool = False) -> None:
        log.info(f"{type(self).__name__} commencing scheme feed consumption.")
        queues.scheme_import_queue.pull(
            self.handle_scheme_tx, raise_exceptions=debug, once=once
        )


class PaymentImportDirector(ImportDirector):
    def handle_payment_tx(self, payment_tx, headers):
        status_monitor.checkin(self)

        session.add(payment_tx)
        session.commit()

        queues.matching_queue.push({"payment_transaction_id": payment_tx.id})
        log.info(
            f"Received, persisted, and enqueued payment transaction #{payment_tx.id}."
        )

        return True

    def enter_loop(self, once: bool = False, debug: bool = False) -> None:
        log.info(f"{type(self).__name__} commencing payment feed consumption.")
        queues.payment_import_queue.pull(
            self.handle_payment_tx, raise_exceptions=debug, once=once
        )
