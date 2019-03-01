from app import models, tasks
from app.db import session
from app.reporting import get_logger
from app.status import status_monitor

log = get_logger("import-director")


class ImportDirector:
    def enter_loop(self, once: bool = False, debug: bool = False) -> None:
        raise NotImplementedError


class SchemeImportDirector(ImportDirector):
    def handle_scheme_transaction(self, scheme_transaction: models.SchemeTransaction) -> None:
        status_monitor.checkin(self)

        session.add(scheme_transaction)
        session.commit()

        tasks.matching_queue.enqueue(tasks.match_scheme_transaction, scheme_transaction.id)

        log.info(f"Received, persisted, and enqueued scheme transaction: {scheme_transaction}.")

        session.close()


class PaymentImportDirector(ImportDirector):
    def handle_payment_transaction(self, payment_transaction: models.PaymentTransaction) -> None:
        status_monitor.checkin(self)

        session.add(payment_transaction)
        session.commit()

        tasks.matching_queue.enqueue(tasks.match_payment_transaction, payment_transaction.id)

        log.info(f"Received, persisted, and enqueued payment transaction #{payment_transaction}.")

        session.close()
