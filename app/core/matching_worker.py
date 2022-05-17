import typing as t

import pendulum
import sentry_sdk

import settings
from app import db, models, tasks
from app.core import identifier
from app.core.export_director import ExportFields, create_export
from app.matching.agents.base import BaseMatchingAgent, MatchResult
from app.matching.agents.registry import matching_agents
from app.registry import NoSuchAgent, RegistryConfigurationError
from app.reporting import get_logger

TransactionType = t.TypeVar("TransactionType", models.PaymentTransaction, models.SchemeTransaction)


class MatchingWorker:
    class LoyaltySchemeNotFound(Exception):
        pass

    class AgentError(Exception):
        pass

    class RedressError(Exception):
        pass

    def __init__(self) -> None:
        self.log = get_logger("matching-worker")

        if settings.DEBUG:
            self.log.warning("Running in debug mode. Exceptions will not be handled gracefully!")

    def _get_agent_for_payment_transaction(
        self, payment_transaction: models.PaymentTransaction, *, session: db.Session
    ) -> t.Optional[BaseMatchingAgent]:
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
                f"{payment_transaction} maps to multiple scheme slugs! This is likely caused by an error in the MIDs. "
                f"Conflicting slugs: {slugs}."
            )

        slug = slugs.pop()

        user_identity = identifier.get_user_identity(payment_transaction.transaction_id, session=session)

        try:
            return matching_agents.instantiate(slug, payment_transaction, user_identity)
        except (NoSuchAgent, RegistryConfigurationError) as ex:
            if settings.DEBUG:
                raise ex
            self.log.warning(
                f"Failed to instantiate matching agent for slug {slug}: {ex}. Skipping match of {payment_transaction}."
            )
            return None

    def _persist(self, matched_transaction: models.MatchedTransaction, *, session: db.Session):
        def add_transaction():
            session.add(matched_transaction)
            session.commit()

        db.run_query(add_transaction, session=session, description="create matched transaction")

        self.log.info(f"Persisted matched transaction #{matched_transaction.id}.")

    def _try_match(self, agent: BaseMatchingAgent, *, session: db.Session) -> t.Optional[MatchResult]:
        try:
            return agent.match(session=session)
        except agent.NoMatchFound:
            return None
        except Exception as ex:
            raise self.AgentError(f"An error occurred when matching with agent {agent}: {ex}") from ex

    def _match(self, payment_transaction: models.PaymentTransaction, *, session: db.Session) -> t.Optional[MatchResult]:
        """
        Attempts to match the given payment transaction.
        Returns the matched transaction on success.
        Raises AgentError if the transaction cannot be matched.
        """
        agent = self._get_agent_for_payment_transaction(payment_transaction, session=session)
        if agent is None:
            return None
        return self._try_match(agent, session=session)

    def _finalise_match(
        self,
        match_result: t.Optional[MatchResult],
        payment_transaction: models.PaymentTransaction,
        *,
        session: db.Session,
    ):
        """
        Given a MatchResult, does the following:
        * Marks the involved payment & scheme transcations as MATCHED
        * Saves the MatchedTransaction to the database
        * Enqueues an export_transaction job to the export queue
        """
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

        self.export_transaction(match_result, session=session)

    def _choose_matching_queue(self, scheme_transactions: t.List[models.SchemeTransaction]):
        """
        Potentially enqueue iceland transactions to the slow matching queue
        """
        matching_queue = tasks.matching_queue  # default queue
        provider_slug = scheme_transactions[0].provider_slug
        if provider_slug in ["iceland-bonus-card"]:
            matching_queue = tasks.matching_slow_queue

        return matching_queue

    def handle_payment_transaction(self, settlement_key: str, *, session: db.Session) -> None:
        """Runs the matching process for a single payment transaction."""
        payment_transaction = db.run_query(
            lambda: session.query(models.PaymentTransaction)
            .filter(models.PaymentTransaction.settlement_key == settlement_key)
            .one_or_none(),
            session=session,
            read_only=True,
            description="find payment transaction",
        )

        if payment_transaction is None:
            self.log.warning(
                f"Failed to load payment transaction with settlement key #{settlement_key} - may be deleted."
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

        self._finalise_match(match_result, payment_transaction, session=session)

    def handle_scheme_transactions(self, match_group: str, *, session: db.Session) -> None:
        """Finds potential matching payment transactions and requeues a matching job for them."""
        scheme_transactions = db.run_query(
            lambda: session.query(models.SchemeTransaction)
            .filter(models.SchemeTransaction.match_group == match_group)
            .all(),
            session=session,
            read_only=True,
            description=f"load scheme transactions for group {match_group}",
        )

        if len(scheme_transactions) == 0:
            self.log.warning(f"Couldn't find any scheme transactions in group {match_group}. Skipping.")
            return

        self.log.debug(f"Received {len(scheme_transactions)} scheme transactions. Looking for potential matches now.")

        mids = {mid for scheme_transaction in scheme_transactions for mid in scheme_transaction.merchant_identifier_ids}

        since = pendulum.now().date().add(days=-14)
        payment_transactions = db.run_query(
            lambda: session.query(models.PaymentTransaction)
            .filter(
                models.PaymentTransaction.merchant_identifier_ids.overlap(mids),
                models.PaymentTransaction.status == models.TransactionStatus.PENDING,
                models.PaymentTransaction.created_at >= since.isoformat(),
            )
            .all(),
            session=session,
            read_only=True,
            description="find pending payment transactions to match scheme transaction",
        )

        if payment_transactions:
            matching_queue = self._choose_matching_queue(scheme_transactions)
            self.log.debug(
                (
                    f"Found {len(payment_transactions)} potential matching payment transactions. Enqueueing matching "
                    f"jobs on {matching_queue.name} queue."
                )
            )
            for payment_transaction in payment_transactions:
                matching_queue.enqueue(tasks.match_payment_transaction, payment_transaction.settlement_key)
        else:
            self.log.debug("Found no matching payment transactions. Exiting matching job.")

    def find_transaction_for_redress(
        self,
        model: t.Type[TransactionType],
        id: int,
        *,
        session: db.Session,
    ) -> TransactionType:
        model_name = model.__name__
        transaction: TransactionType = db.run_query(
            lambda: session.query(model).get(id),
            session=session,
            read_only=True,
            description=f"find {model_name} for redress",
        )

        if transaction is None:
            raise self.RedressError(f"Couldn't find {model_name} with ID #{id}")

        if transaction.status != models.TransactionStatus.PENDING:
            raise self.RedressError(f"Redress attempted on non-pending {model_name} #{id}")

        return transaction

    def _ensure_user_identity(
        self, payment_transaction: models.PaymentTransaction, *, session: db.Session
    ) -> models.UserIdentity:
        if user_identity := identifier.try_get_user_identity(payment_transaction.transaction_id, session=session):
            return user_identity

        try:
            user_info = identifier.payment_card_user_info(
                payment_transaction.merchant_identifier_ids, payment_transaction.card_token, session=session
            )
        except Exception as ex:
            raise self.RedressError(f"Failed to find a user identity for {payment_transaction}: {repr(ex)}") from ex

        try:
            user_identity = identifier.persist_user_identity(
                payment_transaction.transaction_id, user_info, session=session
            )
        except Exception as ex:
            raise self.RedressError(f"Failed to persist user identity for {payment_transaction}: {repr(ex)}") from ex

        return user_identity

    def force_match(self, payment_transaction_id: int, scheme_transaction_id: int, *, session: db.Session):
        """
        Given the IDs of a payment and scheme transaction pair, manually creates a match between them.
        This is used for the missing loyalty redress process.
        """
        payment_transaction = self.find_transaction_for_redress(
            models.PaymentTransaction, payment_transaction_id, session=session
        )

        try:
            user_identity = self._ensure_user_identity(payment_transaction, session=session)
        except Exception as ex:
            self.log.warning(f"_ensure_user_identity raised {repr(ex)}")
            raise ex

        scheme_transaction = self.find_transaction_for_redress(
            models.SchemeTransaction, scheme_transaction_id, session=session
        )

        agent = self._get_agent_for_payment_transaction(payment_transaction, session=session)
        if agent is None:
            raise self.RedressError(f"Failed to find matching agent for {payment_transaction} and {scheme_transaction}")

        self.log.warning(f"Creating forced match of {payment_transaction} and {scheme_transaction}")

        match_result = MatchResult(
            matched_transaction=models.MatchedTransaction(
                **agent.make_matched_transaction_fields(scheme_transaction), matching_type=models.MatchingType.FORCED
            ),
            user_identity=user_identity,
            scheme_transaction_id=scheme_transaction_id,
        )

        self._finalise_match(match_result, payment_transaction, session=session)

    def export_transaction(self, match_result: MatchResult, *, session: db.Session) -> None:
        # Save transactions to export table for ongoing export to merchant
        matched_transaction = match_result.matched_transaction
        user_identity = match_result.user_identity

        payment_scheme_slug = (
            matched_transaction.scheme_transaction.payment_provider_slug
            if matched_transaction.scheme_transaction
            else None
        )

        create_export(
            ExportFields(
                transaction_id=matched_transaction.transaction_id,
                feed_type=None,  # matching has no single feed type
                merchant_slug=matched_transaction.merchant_identifier.loyalty_scheme.slug,
                transaction_date=matched_transaction.transaction_date,
                spend_amount=matched_transaction.spend_amount,
                spend_currency=matched_transaction.spend_currency,
                loyalty_id=user_identity.loyalty_id,
                mid=matched_transaction.merchant_identifier.mid,
                location_id=matched_transaction.merchant_identifier.location_id,
                merchant_internal_id=matched_transaction.merchant_identifier.merchant_internal_id,
                user_id=user_identity.user_id,
                scheme_account_id=user_identity.scheme_account_id,
                payment_card_account_id=user_identity.payment_card_account_id,
                credentials=user_identity.credentials,
                settlement_key=None,
                last_four=user_identity.last_four,
                expiry_month=user_identity.expiry_month,
                expiry_year=user_identity.expiry_year,
                payment_scheme_slug=payment_scheme_slug,
                auth_code=None,
                approval_code=None,
            ),
            session=session,
        )

        def mark_transaction_as_exported():
            matched_transaction.status = models.MatchedTransactionStatus.EXPORTED
            session.commit()

        db.run_query(mark_transaction_as_exported, session=session, description="mark matched transaction as exported")
