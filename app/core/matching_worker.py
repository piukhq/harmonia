import typing as t

import sentry_sdk
import pendulum

from app.matching.agents.registry import matching_agents
from app.matching.agents.base import BaseMatchingAgent, MatchResult
from app.reporting import get_logger
from app.status import status_monitor
from app.registry import NoSuchAgent, RegistryConfigurationError
from app import tasks, models, db
import settings


class MatchingWorker:
    class LoyaltySchemeNotFound(Exception):
        pass

    class AgentError(Exception):
        pass

    def __init__(self) -> None:
        self.log = get_logger("matching-worker")

        if settings.DEBUG:
            self.log.warning("Running in debug mode. Exceptions will not be handled gracefully!")

    def _persist(self, matched_transaction: models.MatchedTransaction, *, session: db.Session):
        def add_transaction():
            session.add(matched_transaction)
            session.commit()

        db.run_query(add_transaction, session=session, description="create matched transaction")

        self.log.info(f"Persisted matched transaction #{matched_transaction.id}.")

    def _try_match(
        self, agent: BaseMatchingAgent, payment_transaction: models.PaymentTransaction, *, session: db.Session
    ) -> t.Optional[MatchResult]:
        try:
            return agent.match(session=session)
        except agent.NoMatchFound:
            return None
        except Exception as ex:
            raise self.AgentError(f"An error occurred when matching with agent {agent}: {ex}") from ex

    def _match(self, payment_transaction: models.PaymentTransaction, *, session: db.Session) -> t.Optional[MatchResult]:
        """Attempts to match the given payment transaction.
        Returns the matched transaction on success.
        Raises UnusableTransaction if the transaction cannot be matched."""
        merchant_identifiers = db.run_query(
            lambda: session.query(models.MerchantIdentifier)
            .filter(models.MerchantIdentifier.id.in_(payment_transaction.merchant_identifier_ids))
            .all(),
            session=session,
            read_only=True,
            description="find payment transaction MIDs",
        )

        slugs = {merchant_identifier.loyalty_scheme.slug for merchant_identifier in merchant_identifiers}

        if len(slugs) > 1:
            raise ValueError(
                f"{payment_transaction} contains multiple scheme slugs! This is likely caused by an error in the MIDs. "
                f"Conflicting slugs: {slugs}."
            )

        slug = slugs.pop()

        try:
            agent = matching_agents.instantiate(slug, payment_transaction)
        except (NoSuchAgent, RegistryConfigurationError) as ex:
            if settings.DEBUG:
                raise ex
            self.log.warning(
                f"Failed to instantiate matching agent for slug {slug}: {ex}. Skipping match of {payment_transaction}."
            )
            return None

        return self._try_match(agent, payment_transaction, session=session)

    def handle_payment_transaction(self, payment_transaction_id: int, *, session: db.Session) -> None:
        """Runs the matching process for a single payment transaction."""
        status_monitor.checkin(self)

        payment_transaction = db.run_query(
            lambda: session.query(models.PaymentTransaction).get(payment_transaction_id),
            session=session,
            read_only=True,
            description="find payment transaction",
        )

        if payment_transaction is None:
            self.log.warning(
                f"Failed to load payment transaction #{payment_transaction_id} - record may have been deleted."
            )
            return

        self.log.debug(f"Received payment transaction #{payment_transaction.id}. Attempting to match…")

        if payment_transaction.status == models.TransactionStatus.MATCHED:
            self.log.debug(f"Payment transaction #{payment_transaction.id} has already been matched. Ignoring.")
            return

        match_result = None
        try:
            match_result = self._match(payment_transaction, session=session)
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

        self.log.debug("Matching succeeded! Marking transactions as matched.")

        def mark_transactions():
            payment_transaction.status = models.TransactionStatus.MATCHED

            # spotted transactions don't have a matching scheme transaction
            if match_result.scheme_transaction_id is not None:
                scheme_transaction = session.query(models.SchemeTransaction).get(match_result.scheme_transaction_id)
                scheme_transaction.status = models.TransactionStatus.MATCHED

            session.commit()

        db.run_query(mark_transactions, session=session, description="mark scheme transaction as matched")

        self.log.debug("Persisting matched transaction.")
        self._persist(match_result.matched_transaction, session=session)

        tasks.export_queue.enqueue(tasks.export_matched_transaction, match_result.matched_transaction.id)

    def handle_scheme_transactions(self, from_date: pendulum.DateTime, *, session: db.Session) -> None:
        """Finds potential matching payment transactions and requeues a matching job for them."""
        status_monitor.checkin(self)

        scheme_transactions = db.run_query(
            lambda: session.query(models.SchemeTransaction)
            .filter(models.SchemeTransaction.created_at >= from_date)
            .all(),
            session=session,
            read_only=True,
            description=f"find scheme transactions from {from_date}",
        )

        if len(scheme_transactions) == 0:
            self.log.warning(f"Couldn't find any scheme transaction from {from_date}. Skipping.")
            return

        self.log.debug(f"Received {len(scheme_transactions)} scheme transactions. Looking for potential matches now.")

        mids = {mid for scheme_transaction in scheme_transactions for mid in scheme_transaction.merchant_identifier_ids}

        payment_transactions = db.run_query(
            lambda: session.query(models.PaymentTransaction)
            .filter(
                models.PaymentTransaction.merchant_identifier_ids.overlap(mids),
                models.PaymentTransaction.status == models.TransactionStatus.PENDING,
                models.PaymentTransaction.user_identity_id.isnot(None),
            )
            .all(),
            session=session,
            read_only=True,
            description="find pending payment transactions to match scheme transaction",
        )

        if payment_transactions:
            self.log.debug(
                f"Found {len(payment_transactions)} potential matching payment transactions. Enqueueing matching jobs."
            )
            for payment_transaction in payment_transactions:
                tasks.matching_queue.enqueue(tasks.match_payment_transaction, payment_transaction.id)
        else:
            self.log.debug("Found no matching payment transactions. Exiting matching job.")
