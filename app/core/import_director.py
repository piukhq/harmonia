from app import models, tasks, db
from app.reporting import get_logger
from app.status import status_monitor

log = get_logger("import-director")


class SchemeImportDirector:
    def handle_scheme_transaction(self, scheme_transaction: models.SchemeTransaction) -> None:
        status_monitor.checkin(self)

        def add_transaction():
            db.session.add(scheme_transaction)
            db.session.commit()

        db.run_query(add_transaction)

        tasks.matching_queue.enqueue(tasks.match_scheme_transaction, scheme_transaction.id)

        log.info(f"Received, persisted, and enqueued {scheme_transaction}.")


class PaymentImportDirector:
    def handle_payment_transaction(self, payment_transaction: models.PaymentTransaction) -> None:
        status_monitor.checkin(self)

        def add_transaction():
            db.session.add(payment_transaction)
            db.session.commit()

        db.run_query(add_transaction)

        tasks.matching_queue.enqueue(tasks.match_payment_transaction, payment_transaction.id)

        log.info(f"Received, persisted, and enqueued {payment_transaction}.")
