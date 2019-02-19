import typing as t

import sentry_sdk

from app.db import session
from app.matching.agents.registry import matching_agents
from app.matching.agents.base import BaseMatchingAgent, MatchResult
from app.reporting import get_logger
from app.status import status_monitor
from app import tasks, models
import settings


class MatchingWorker:
    class LoyaltySchemeNotFound(Exception):
        pass

    class AgentError(Exception):
        pass

    def __init__(self) -> None:
        self.log = get_logger(f"matching-worker")

        if settings.DEBUG:
            self.log.warning(
                "Running in debug mode. Exceptions will not be handled gracefully!"
            )

    def _persist(self, matched_tx: models.MatchedTransaction):
        session.add(matched_tx)
        session.commit()
        self.log.info(f"Persisted matched transaction #{matched_tx.id}.")

    def _try_match(
        self, agent: BaseMatchingAgent, payment_tx: models.PaymentTransaction
    ) -> t.Optional[MatchResult]:
        try:
            return agent.match()
        except agent.NoMatchFound:
            return None
        except Exception as ex:
            raise self.AgentError(
                f"An error occurred when matching with agent {agent}: {ex}"
            ) from ex

    def _match(
        self, payment_tx: models.PaymentTransaction
    ) -> t.Optional[MatchResult]:
        """Attempts to match the given payment transaction.
        Returns the matched transaction on success.
        Raises UnusableTransaction if the transaction cannot be matched."""
        merchant_identifiers = session.query(models.MerchantIdentifier).filter(
            models.MerchantIdentifier.id.in_(
                payment_tx.merchant_identifier_ids
            )
        )

        slugs = [
            merchant_identifier.payment_provider.slug
            for merchant_identifier in merchant_identifiers
        ]

        slugs_differ = len(set(slugs)) > 1
        if slugs_differ:
            raise ValueError(
                f"{payment_tx} contains multiple scheme slugs! This is likely caused by an error in the MIDs. "
                f"Conflicting slugs: {set(slugs)}"
            )

        slug = slugs[0]
        agent = matching_agents.instantiate(slug, payment_tx)
        return self._try_match(agent, payment_tx)

    def _identify(self, matched_tx: models.MatchedTransaction) -> None:
        self._persist(matched_tx)
        tasks.matching_queue.enqueue(
            tasks.identify_matched_transaction, matched_tx.id
        )

    def handle_payment_transaction(self, payment_transaction_id: int) -> None:
        """Runs the matching process for a single payment transaction."""
        status_monitor.checkin(self)

        payment_tx = session.query(models.PaymentTransaction).get(
            payment_transaction_id
        )

        self.log.debug(
            f"Received payment transaction #{payment_tx.id}. Attempting to match…"
        )

        if payment_tx.status == models.TransactionStatus.MATCHED:
            self.log.debug(
                f"Payment transaction #{payment_tx.id} has already been matched. Ignoring."
            )
            session.close()
            return

        match_result = None
        try:
            match_result = self._match(payment_tx)
        except self.AgentError as ex:
            if settings.DEBUG:
                raise ex
            else:
                event_id = sentry_sdk.capture_exception(ex)
                self.log.error(
                    f"Failed to match payment transaction #{payment_tx.id}: {ex}. Sentry issue ID: {event_id}."
                )

        if match_result is None:
            self.log.info("Failed to find any matches.")
            session.close()
            return

        self.log.debug(f"Matching succeeded! Marking transactions as matched.")
        payment_tx.status = models.TransactionStatus.MATCHED

        scheme_tx = session.query(models.SchemeTransaction).get(
            match_result.scheme_tx_id
        )
        scheme_tx.status = models.TransactionStatus.MATCHED
        session.commit()

        self.log.debug(
            f"Persisting & identifying payment transaction #{payment_tx.id}."
        )
        self._identify(match_result.matched_tx)

        session.close()

    def handle_scheme_transaction(self, scheme_transaction_id: int) -> None:
        """Finds potential matching payment transactions and requeues a matching job for them."""
        status_monitor.checkin(self)

        scheme_transaction = session.query(models.SchemeTransaction).get(
            scheme_transaction_id
        )

        self.log.debug(
            f"Received scheme transaction #{scheme_transaction.id}. Finding potential matches…"
        )

        payment_transactions = session.query(models.PaymentTransaction).filter(
            models.PaymentTransaction.merchant_identifier_ids.overlap(
                scheme_transaction.merchant_identifier_ids
            ),
            models.PaymentTransaction.status
            == models.TransactionStatus.PENDING,
        )

        if payment_transactions:
            self.log.debug(
                f"Found {payment_transactions.count()} potential matches. Enqueueing matching jobs."
            )
            for payment_transaction in payment_transactions:
                tasks.matching_queue.enqueue(
                    tasks.match_payment_transaction, payment_transaction.id
                )

        session.close()
