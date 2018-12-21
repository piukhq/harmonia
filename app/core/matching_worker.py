import typing as t

import sentry_sdk

from app.db import session
from app.matching.agents.active import AGENTS
from app.matching.agents.base import BaseMatchingAgent, MatchResult
from app.models import (
    MatchedTransaction,
    PaymentTransaction,
    SchemeTransaction,
    TransactionStatus,
)
from app.reporting import get_logger
from app.status import status_monitor
from app import tasks
import settings


class MatchingWorker:
    class LoyaltySchemeNotFound(Exception):
        pass

    class NoMatchingAgent(Exception):
        pass

    class AgentError(Exception):
        pass

    def __init__(self) -> None:
        self.log = get_logger(f"matching-worker")

        if settings.DEBUG:
            self.log.warning(
                "Running in debug mode. Exceptions will not be handled gracefully!"
            )

    def _persist(self, matched_tx: MatchedTransaction):
        session.add(matched_tx)
        session.commit()
        self.log.info(f"Persisted matched transaction #{matched_tx.id}.")

    def _find_agent(self, slug: str) -> t.Type[BaseMatchingAgent]:
        try:
            return AGENTS[slug]
        except KeyError as ex:
            raise self.NoMatchingAgent(
                f"No matching agent is registered for slug {repr(slug)}"
            ) from ex

    def _try_match(
        self, agent: BaseMatchingAgent, payment_tx: PaymentTransaction
    ) -> t.Optional[MatchResult]:
        try:
            return agent.match()
        except agent.NoMatchFound:
            return None
        except Exception as ex:
            raise self.AgentError(
                f"An error occurred when matching with agent {agent}: {ex}"
            ) from ex

    def _match(self, payment_tx: PaymentTransaction) -> t.Optional[MatchResult]:
        """Attempts to match the given payment transaction.
        Returns the matched transaction on success.
        Raises UnusableTransaction if the transaction cannot be matched."""
        slug = payment_tx.merchant_identifier.loyalty_scheme.slug
        agent_class = self._find_agent(slug)
        agent = agent_class(payment_tx)
        return self._try_match(agent, payment_tx)

    def _export(self, matched_tx: MatchedTransaction) -> None:
        self._persist(matched_tx)
        tasks.export_queue.enqueue(tasks.export_matched_transaction, matched_tx.id)

    def handle_payment_transaction(self, payment_transaction_id: int) -> None:
        """Runs the matching process for a single payment transaction."""
        status_monitor.checkin(self)

        payment_tx = session.query(PaymentTransaction).get(payment_transaction_id)

        self.log.debug(
            f"Received payment transaction #{payment_tx.id}. Attempting to match…"
        )

        if payment_tx.status == TransactionStatus.MATCHED:
            self.log.debug(
                f"Payment transaction #{payment_tx.id} has already been matched. Ignoring."
            )
            session.close()
            return

        match_result = None
        try:
            match_result = self._match(payment_tx)
        except (self.NoMatchingAgent, self.AgentError) as ex:
            if settings.DEBUG:
                raise ex
            else:
                sentry_id = sentry_sdk.capture_exception(ex)
                self.log.error(
                    f"Failed to match payment transaction #{payment_tx.id}: {ex}. Sentry issue ID: {sentry_id}."
                )

        if match_result is None:
            self.log.info("Failed to find any matches.")
            session.close()
            return

        self.log.debug(f"Matching succeeded! Marking transactions as matched.")
        payment_tx.status = TransactionStatus.MATCHED

        scheme_tx = session.query(SchemeTransaction).get(match_result.scheme_tx_id)
        scheme_tx.status = TransactionStatus.MATCHED
        session.commit()

        self.log.debug(f"Persisting & exporting payment transaction #{payment_tx.id}.")
        self._export(match_result.matched_tx)

        session.close()

    def handle_scheme_transaction(self, scheme_transaction_id: int) -> None:
        """Finds potential matching payment transactions and requeues a matching job for them."""
        status_monitor.checkin(self)

        scheme_transaction = session.query(SchemeTransaction).get(scheme_transaction_id)

        self.log.debug(
            f"Received scheme transaction #{scheme_transaction.id}. Finding potential matches…"
        )

        payment_transactions = session.query(PaymentTransaction).filter(
            PaymentTransaction.merchant_identifier_id
            == scheme_transaction.merchant_identifier_id,
            PaymentTransaction.status == TransactionStatus.PENDING,
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
