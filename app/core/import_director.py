import typing as t

from app import db, models, tasks
from app.reporting import get_logger
from app.status import status_monitor

log = get_logger("import-director")


class SchemeImportDirector:
    def handle_scheme_transactions(
        self, scheme_transactions: t.List[models.SchemeTransaction], *, match_group: str, session: db.Session
    ) -> None:
        status_monitor.checkin(self)

        def add_transactions():
            session.bulk_save_objects(scheme_transactions)
            session.commit()

        db.run_query(add_transactions, session=session, description="create scheme transaction")

        tasks.matching_queue.enqueue(tasks.match_scheme_transactions, match_group=match_group)

        log.info(
            f"Received, persisted, and enqueued {len(scheme_transactions)} scheme transactions in group {match_group}."
        )


class PaymentImportDirector:
    class InvalidAuthTransaction(Exception):
        pass

    @staticmethod
    def _get_matching_transaction(*, settlement_key: str, session: db.Session) -> t.Optional[models.PaymentTransaction]:
        return db.run_query(
            lambda: session.query(models.PaymentTransaction)
            .filter(models.PaymentTransaction.settlement_key == settlement_key)
            .one_or_none(),
            session=session,
            read_only=True,
            description="find matching payment transaction",
        )

    @staticmethod
    def _override_auth_transaction(
        auth_transaction: models.PaymentTransaction,
        settled_transaction: models.PaymentTransaction,
        *,
        session: db.Session,
    ):
        log.info(
            f"Overriding auth transaction {auth_transaction} "
            f"with fields from matching settled transaction: {settled_transaction}"
        )

        def update_transaction():
            # TODO: what other fields need to be updated?
            auth_transaction.spend_amount = settled_transaction.spend_amount
            auth_transaction.transaction_id = settled_transaction.transaction_id

            if not auth_transaction.first_six and settled_transaction.first_six:
                auth_transaction.first_six = settled_transaction.first_six

            if not auth_transaction.last_four and settled_transaction.last_four:
                auth_transaction.last_four = settled_transaction.last_four

            if not auth_transaction.auth_code and settled_transaction.auth_code:
                auth_transaction.auth_code = settled_transaction.auth_code

            session.commit()

        db.run_query(update_transaction, session=session, description="override auth transaction fields")

    def handle_auth_payment_transaction(
        self, auth_transaction: models.PaymentTransaction, *, session: db.Session
    ) -> None:
        status_monitor.checkin(self)

        if auth_transaction.settlement_key is None:
            raise self.InvalidAuthTransaction(
                f"Auth transaction {auth_transaction} has no settlement key! "
                "This field should be set by the import agent."
            )

        tasks.identify_user_queue.enqueue(tasks.identify_user,
                                          auth_transaction.settlement_key,
                                          auth_transaction.merchant_identifier_ids)

        settled_transaction = self._get_matching_transaction(
            settlement_key=auth_transaction.settlement_key, session=session
        )
        if settled_transaction:
            log.info(
                f"Skipping import of auth transaction {auth_transaction} "
                f"as a settled transaction was found: {settled_transaction}"
            )
            return

        log.debug(f"No settled transaction was found for auth transaction {auth_transaction}.")

        def add_transaction():
            session.add(auth_transaction)
            session.commit()

        db.run_query(add_transaction, session=session, description="create auth payment transaction")

        # tasks.matching_queue.enqueue(tasks.identify_payment_transaction, auth_transaction.id)

        log.info(f"Received, persisted, and enqueued matching job for auth transaction {auth_transaction}.")

    def handle_settled_payment_transaction(
        self, settled_transaction: models.PaymentTransaction, *, session: db.Session
    ) -> None:
        status_monitor.checkin(self)

        if settled_transaction.settlement_key is not None:
            auth_transaction = self._get_matching_transaction(
                settlement_key=settled_transaction.settlement_key, session=session
            )
        else:
            auth_transaction = None

        if auth_transaction:
            if auth_transaction.status == models.TransactionStatus.PENDING:
                self._override_auth_transaction(auth_transaction, settled_transaction, session=session)
                log.info(f"Re-queuing matching job for {auth_transaction}")
                tasks.matching_queue.enqueue(tasks.match_payment_transaction, auth_transaction.id)
            else:
                log.info(
                    f"Skipping import of settled transaction {settled_transaction} "
                    f"as a matched auth transaction was found: {auth_transaction}"
                )
                return
        else:
            log.debug(f"No auth transaction was found for settled transaction {settled_transaction}.")

            def add_transaction():
                session.add(settled_transaction)
                session.commit()

            db.run_query(add_transaction, session=session, description="create settled transaction")
            tasks.matching_queue.enqueue(tasks.identify_payment_transaction, settled_transaction.id)

        log.info(f"Received, persisted, and enqueued settled transaction {settled_transaction}.")
