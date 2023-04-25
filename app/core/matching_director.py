import typing as t

from app import db, models, tasks
from app.feeds import FeedType
from app.reporting import get_logger

log = get_logger("matching-director")


class MatchingDirector:
    class ImportError(Exception):
        pass

    def get_feed_type_handler(self, feed_type: FeedType) -> t.Callable[[list[models.Transaction], str], None]:
        return {
            FeedType.AUTH: self.handle_auth_transactions,
            FeedType.SETTLED: self.handle_settled_transactions,
            FeedType.MERCHANT: self.handle_merchant_transactions,
        }[feed_type]

    def handle_transaction(
        self, transaction_id: str, feed_type: FeedType, match_group: str, *, session: db.Session
    ) -> None:
        log.info(f"Matching director handling {feed_type.name} transaction #{transaction_id}")

        transaction = self._load_transaction(transaction_id, feed_type, session=session)
        log.debug(f"Loaded {feed_type.name} transaction: {transaction}")

        handler = self.get_feed_type_handler(feed_type)
        handler([transaction], match_group)

    def handle_transactions(self, match_group: str, *, session: db.Session) -> None:
        log.info(f"Matching director handling transaction group #{match_group}")

        transactions = self._load_transactions(match_group, session=session)
        feed_types = {tx.feed_type for tx in transactions}

        if len(feed_types) > 1:
            raise self.ImportError(
                "Received match group with mixed feed types: #{match_group}. "
                "This indicates a problem in the import agent base."
            )

        feed_type = feed_types.pop()
        log.debug(f"Loaded {len(transactions)} {feed_type.name} transactions")

        handler = self.get_feed_type_handler(feed_type)
        handler(transactions, match_group)

        log.debug(f"Successfully enqueued matching job for {len(transactions)} {feed_type.name} transactions.")

    def handle_auth_transactions(self, transactions: list[models.Transaction], match_group: str) -> None:
        self._handle_payment_transactions(
            transactions, match_group, routing_task=tasks.persist_auth_payment_transactions
        )

    def handle_settled_transactions(self, transactions: list[models.Transaction], match_group: str) -> None:
        self._handle_payment_transactions(
            transactions, match_group, routing_task=tasks.persist_settled_payment_transactions
        )

    def handle_merchant_transactions(self, transactions: list[models.Transaction], match_group: str) -> None:
        scheme_transactions = [
            models.SchemeTransaction(
                merchant_identifier_ids=transaction.merchant_identifier_ids,
                primary_identifier=transaction.primary_identifier,
                provider_slug=transaction.merchant_slug,
                payment_provider_slug=transaction.payment_provider_slug,
                transaction_id=transaction.transaction_id,
                transaction_date=transaction.transaction_date,
                has_time=transaction.has_time,
                spend_amount=transaction.spend_amount,
                spend_multiplier=transaction.spend_multiplier,
                spend_currency=transaction.spend_currency,
                first_six=transaction.first_six,
                last_four=transaction.last_four,
                status=models.TransactionStatus.PENDING,
                auth_code=transaction.auth_code,
                match_group=match_group,
                extra_fields=transaction.extra_fields,
            )
            for transaction in transactions
        ]
        tasks.matching_queue.enqueue(tasks.persist_scheme_transactions, scheme_transactions, match_group=match_group)

    def _handle_payment_transactions(
        self, transactions: list[models.Transaction], match_group: str, *, routing_task: t.Callable
    ) -> None:
        payment_transactions = [
            models.PaymentTransaction(
                merchant_identifier_ids=transaction.merchant_identifier_ids,
                primary_identifier=transaction.primary_identifier,
                provider_slug=transaction.payment_provider_slug,
                transaction_id=transaction.transaction_id,
                settlement_key=transaction.settlement_key,
                transaction_date=transaction.transaction_date,
                has_time=transaction.has_time,
                spend_amount=transaction.spend_amount,
                spend_multiplier=transaction.spend_multiplier,
                spend_currency=transaction.spend_currency,
                card_token=transaction.card_token,
                first_six=transaction.first_six,
                last_four=transaction.last_four,
                status=models.TransactionStatus.PENDING,
                auth_code=transaction.auth_code,
                approval_code=transaction.approval_code,
                match_group=match_group,
                extra_fields=transaction.extra_fields,
            )
            for transaction in transactions
        ]
        tasks.matching_queue.enqueue(routing_task, payment_transactions, match_group=match_group)

    def _load_transaction(self, transaction_id: str, feed_type: FeedType, *, session: db.Session) -> models.Transaction:
        q = session.query(models.Transaction).filter(
            models.Transaction.transaction_id == transaction_id, models.Transaction.feed_type == feed_type
        )
        return db.run_query(
            q.one,
            session=session,
            read_only=True,
            description=f"load transaction #{transaction_id} for import into the matching system",
        )

    def _load_transactions(self, match_group: str, *, session: db.Session) -> models.Transaction:
        q = session.query(models.Transaction).filter(models.Transaction.match_group == match_group)
        return db.run_query(
            q.all,
            session=session,
            read_only=True,
            description=f"load transactions in group #{match_group} for import into the matching system",
        )


class SchemeMatchingDirector:
    def handle_scheme_transactions(
        self, scheme_transactions: t.List[models.SchemeTransaction], *, match_group: str, session: db.Session
    ) -> None:
        def add_transactions():
            session.bulk_save_objects(scheme_transactions)
            session.commit()

        db.run_query(add_transactions, session=session, description="create scheme transaction")

        tasks.matching_queue.enqueue(tasks.match_scheme_transactions, match_group=match_group)


class PaymentMatchingDirector:
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
        if auth_transaction.settlement_key is None:
            raise self.InvalidAuthTransaction(
                f"Auth transaction {auth_transaction} has no settlement key! "
                "This field should be set by the import agent."
            )

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

        tasks.matching_queue.enqueue(tasks.match_payment_transaction, auth_transaction.settlement_key)

    def handle_settled_payment_transaction(
        self, settled_transaction: models.PaymentTransaction, *, session: db.Session
    ) -> None:
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
                tasks.matching_queue.enqueue(tasks.match_payment_transaction, auth_transaction.settlement_key)
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

            tasks.matching_queue.enqueue(tasks.match_payment_transaction, settled_transaction.settlement_key)
