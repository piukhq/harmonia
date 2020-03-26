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

        db.run_query(add_transaction, description="create scheme transaction")

        tasks.matching_queue.enqueue(tasks.match_scheme_transaction, scheme_transaction.id)

        log.info(f"Received, persisted, and enqueued {scheme_transaction}.")


class PaymentImportDirector:
    def handle_auth_payment_transaction(self, auth_transaction: models.PaymentTransaction) -> None:
        status_monitor.checkin(self)

        def get_settled_transaction():
            return (
                db.session.query(models.PaymentTransaction)
                .filter(models.PaymentTransaction.settlement_key == auth_transaction.settlement_key)
                .one()
            )

        settled_transaction: models.PaymentTransaction = db.run_query(
            get_settled_transaction, description="find settled transaction"
        )
        if settled_transaction:
            log.info(
                f"Skipping import of auth transaction {auth_transaction} "
                f"as a settled transaction was found: {settled_transaction}"
            )
            return

        log.debug(f"No settled transaction was found for auth transaction {auth_transaction}.")

        def add_transaction():
            db.session.add(auth_transaction)
            db.session.commit()

        db.run_query(add_transaction, description="create auth payment transaction")

        tasks.matching_queue.enqueue(tasks.identify_payment_transaction, auth_transaction.id)

        log.info(f"Received, persisted, and enqueued matching job for auth transaction {auth_transaction}.")

    def handle_settled_payment_transaction(self, settled_transaction: models.PaymentTransaction) -> None:
        status_monitor.checkin(self)

        def get_auth_transaction():
            return (
                db.session.query(models.PaymentTransaction)
                .filter(models.PaymentTransaction.settlement_key == settled_transaction.settlement_key)
                .one()
            )

        auth_transaction: models.PaymentTransaction = db.run_query(
            get_auth_transaction, description="find auth transaction"
        )

        def override_auth_transaction():
            # TODO: what other fields need to be updated?
            auth_transaction.spend_amount = settled_transaction.spend_amount
            db.session.commit()

        if auth_transaction:
            if auth_transaction.status == models.TransactionStatus.PENDING:
                log.info(
                    "Overriding pending auth transaction {auth_transaction} "
                    f"with fields from matching settled transaction: {settled_transaction}"
                )
                db.run_query(override_auth_transaction, description="override auth transaction fields")
            else:
                log.info(
                    f"Skipping import of settled transaction {settled_transaction} "
                    f"as a matched auth transaction was found: {auth_transaction}"
                )
                return
        else:
            log.debug(f"No auth transaction was found for settled transaction {settled_transaction}.")

            def add_transaction():
                db.session.add(settled_transaction)
                db.session.commit()

            db.run_query(add_transaction, description="create settled transaction")

        tasks.matching_queue.enqueue(tasks.identify_payment_transaction, settled_transaction.id)

        log.info(f"Received, persisted, and enqueued settled transaction {settled_transaction}.")
