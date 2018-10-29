import typing as t

import humanize
import pendulum
import sentry_sdk

from app.db import Session
from app.matching import retry
from app.matching.agents.active import AGENTS
from app.matching.agents.base import BaseMatchingAgent
from app.models import MatchedTransaction, PaymentTransaction
from app.queues import export_queue, matching_queue
from app.reporting import get_logger
from app.status import status_monitor

session = Session()


class MatchingWorker:
    class LoyaltySchemeNotFound(Exception):
        pass

    class NoMatchingAgent(Exception):
        pass

    class AgentError(Exception):
        pass

    def __init__(self, name: str, debug: bool = False) -> None:
        self.name = name
        self.debug = debug

        self.log = get_logger(f"matching-worker.{self.name}")

        if self.debug:
            self.log.warning('Running in debug mode. Exceptions will not be handled gracefully!')

    @staticmethod
    def _get_retry_delay(retry_count: int) -> int:
        return (2**retry_count) * 60  # starts at 60 seconds and doubles with each retry

    def _retry(self, payment_tx: PaymentTransaction, headers: dict):
        try:
            last_try = headers['X-Retried-At']
        except KeyError:
            last_try = headers['X-Queued-At']

        retry_count = headers['X-Retry-Count']
        delay = self._get_retry_delay(retry_count)
        retry_at = last_try + delay

        when = humanize.naturaltime(delay, future=True)

        self.log.info(f"Payment transaction #{payment_tx.id} has been retried {retry_count} time(s) "
                      f"and was last tried at {pendulum.from_timestamp(last_try)}. "
                      f"Storing a retry entry to try again {when} at {pendulum.from_timestamp(retry_at)}.")

        retry.store(payment_tx.id, retry.RetryEntry(retry_at, retry_count, headers['X-Queued-At']))

    def _persist(self, matched_tx: MatchedTransaction):
        self.log.critical(f"Would persist {repr(matched_tx)}!")
        session.add(matched_tx)
        session.commit()
        self.log.info(f"Persisted matched transaction #{matched_tx.id}")

    def _find_agent(self, slug: str) -> BaseMatchingAgent:
        try:
            return AGENTS[slug]
        except KeyError as ex:
            raise self.NoMatchingAgent(f"No matching agent is registered for slug {repr(slug)}") from ex

    def _try_match(self, agent: BaseMatchingAgent, payment_tx: PaymentTransaction) -> t.Optional[MatchedTransaction]:
        try:
            return agent.match()
        except agent.NoMatchFound:
            return None
        except Exception as ex:
            raise self.AgentError(f"An error occurred when matching with agent {repr(agent)}") from ex

    def _match(self, payment_tx: PaymentTransaction) -> t.Optional[MatchedTransaction]:
        """Attempts to match the given payment transaction.
        Returns the matched transaction on success.
        Raises UnusableTransaction if the transaction cannot be matched."""
        slug = payment_tx.merchant_identifier.loyalty_scheme.slug
        agent_class = self._find_agent(slug)
        agent = agent_class(payment_tx)
        return self._try_match(agent, payment_tx)

    def _export(self, matched_tx: MatchedTransaction) -> None:
        self._persist(matched_tx)
        export_queue.push(matched_tx)

    def handle_transaction(self, payment_tx: PaymentTransaction, headers: dict) -> bool:
        """Runs the matching process for a single payment transaction."""
        status_monitor.checkin(self, suffix=self.name)

        self.log.debug(f"Received payment transaction #{payment_tx.id}. Attempting to match…")

        try:
            matched_tx = self._match(payment_tx)
        except (self.NoMatchingAgent, self.AgentError) as ex:
            sentry_id = sentry_sdk.capture_exception(ex)
            self.log.error(f"Failed to match payment transaction #{payment_tx.id}: {ex}. Sentry issue ID: {sentry_id}.")
            should_retry = True

        if should_retry is True or matched_tx is None:
            self.log.debug(f"Matching failed, submitting payment transaction #{payment_tx.id} for retry")
            self._retry(payment_tx, headers)
            return True

        self.log.debug(f"Matching succeeded! Persisting & exporting payment transaction #{payment_tx.id}")
        self._export(matched_tx)

        return True

    def enter_loop(self) -> None:
        self.log.info(f"{type(self).__name__} commencing matching feed consumption")
        matching_queue.pull(self.handle_transaction, raise_exceptions=self.debug)
