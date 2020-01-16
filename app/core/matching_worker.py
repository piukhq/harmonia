import typing as t

import sentry_sdk

from app.matching.agents.registry import matching_agents
from app.matching.agents.base import BaseMatchingAgent, MatchResult
from app.reporting import get_logger
from app.status import status_monitor
from app import tasks, models, db
import settings


class MatchingWorker:
    class LoyaltySchemeNotFound(Exception):
        pass

    class AgentError(Exception):
        pass

    def __init__(self) -> None:
        self.log = get_logger(f"matching-worker")

        if settings.DEBUG:
            self.log.warning("Running in debug mode. Exceptions will not be handled gracefully!")

    def _persist(self, matched_transaction: models.MatchedTransaction):
        def add_transaction():
            db.session.add(matched_transaction)
            db.session.commit()

        db.run_query(add_transaction)

        self.log.info(f"Persisted matched transaction #{matched_transaction.id}.")

    def _try_match(
        self, agent: BaseMatchingAgent, payment_transaction: models.PaymentTransaction
    ) -> t.Optional[MatchResult]:
        try:
            return agent.match()
        except agent.NoMatchFound:
            return None
        except Exception as ex:
            raise self.AgentError(f"An error occurred when matching with agent {agent}: {ex}") from ex

    def _match(self, payment_transaction: models.PaymentTransaction) -> t.Optional[MatchResult]:
        """Attempts to match the given payment transaction.
        Returns the matched transaction on success.
        Raises UnusableTransaction if the transaction cannot be matched."""
        merchant_identifiers = db.run_query(
            lambda: db.session.query(models.MerchantIdentifier).filter(
                models.MerchantIdentifier.id.in_(payment_transaction.merchant_identifier_ids)
            ).all()
        )

        slugs = [merchant_identifier.payment_provider.slug for merchant_identifier in merchant_identifiers]

        slugs_differ = len(set(slugs)) > 1
        if slugs_differ:
            raise ValueError(
                f"{payment_transaction} contains multiple scheme slugs! This is likely caused by an error in the MIDs. "
                f"Conflicting slugs: {set(slugs)}"
            )

        slug = slugs[0]
        agent = matching_agents.instantiate(slug, payment_transaction)
        return self._try_match(agent, payment_transaction)

    def _identify(self, matched_transaction: models.MatchedTransaction) -> None:
        self._persist(matched_transaction)
        tasks.matching_queue.enqueue(tasks.identify_matched_transaction, matched_transaction.id)

    def handle_payment_transaction(self, payment_transaction_id: int) -> None:
        """Runs the matching process for a single payment transaction."""
        status_monitor.checkin(self)

        payment_transaction = db.run_query(
            lambda: db.session.query(models.PaymentTransaction).get(payment_transaction_id)
        )

        if payment_transaction is None:
            self.log.warning(f"Couldn't find a payment transaction with ID {payment_transaction_id}. Skipping.")
            return

        self.log.debug(f"Received payment transaction #{payment_transaction.id}. Attempting to match…")

        if payment_transaction.status == models.TransactionStatus.MATCHED:
            self.log.debug(f"Payment transaction #{payment_transaction.id} has already been matched. Ignoring.")
            return

        match_result = None
        try:
            match_result = self._match(payment_transaction)
        except self.AgentError as ex:
            if settings.DEBUG:
                raise ex
            else:
                event_id = sentry_sdk.capture_exception(ex)
                self.log.error(
                    f"Failed to match payment transaction #{payment_transaction.id}: {ex}. Sentry issue ID: {event_id}."
                )

        if match_result is None:
            self.log.info("Failed to find any matches.")
            return

        self.log.debug(f"Matching succeeded! Marking transactions as matched.")

        def mark_transactions():
            payment_transaction.status = models.TransactionStatus.MATCHED

            scheme_transaction = db.session.query(models.SchemeTransaction).get(match_result.scheme_transaction_id)
            scheme_transaction.status = models.TransactionStatus.MATCHED
            db.session.commit()

        db.run_query(mark_transactions)

        self.log.debug(f"Persisting & identifying payment transaction #{payment_transaction.id}.")
        self._identify(match_result.matched_transaction)

    def handle_scheme_transaction(self, scheme_transaction_id: int) -> None:
        """Finds potential matching payment transactions and requeues a matching job for them."""
        status_monitor.checkin(self)

        scheme_transaction = db.run_query(lambda: db.session.query(models.SchemeTransaction).get(scheme_transaction_id))

        if scheme_transaction is None:
            self.log.warning(f"Couldn't find a scheme transaction with ID {scheme_transaction_id}. Skipping.")
            return

        self.log.debug(f"Received scheme transaction #{scheme_transaction.id}. Finding potential matches…")

        payment_transactions = db.run_query(
            lambda: db.session.query(models.PaymentTransaction).filter(
                models.PaymentTransaction.merchant_identifier_ids.overlap(scheme_transaction.merchant_identifier_ids),
                models.PaymentTransaction.status == models.TransactionStatus.PENDING,
            ).all()
        )

        if payment_transactions:
            self.log.debug(f"Found {payment_transactions.count()} potential matches. Enqueueing matching jobs.")
            for payment_transaction in payment_transactions:
                tasks.matching_queue.enqueue(tasks.match_payment_transaction, payment_transaction.id)
