import pendulum
import typing as t
from collections import namedtuple

from app.reporting import get_logger
from app import models, db

MatchResult = namedtuple("MatchResult", ("matched_transaction", "scheme_transaction_id"))


class BaseMatchingAgent:
    class NoMatchFound(Exception):
        pass

    def __init__(self, payment_transaction: models.PaymentTransaction) -> None:
        """Matching agents are expected to query for their own SchemeTransaction objects based on properties of the
        given payment transaction."""
        self.payment_transaction = payment_transaction
        self.log = get_logger(f"matching-agent.{type(self).__name__}")

    def __repr__(self) -> str:
        return f"{type(self).__name__}(payment_transaction={repr(self.payment_transaction)})"

    def __str__(self) -> str:
        return f"{type(self).__name__}"

    def _get_scheme_transactions(self, *, session: db.Session, **search_fields) -> t.List[models.SchemeTransaction]:
        search_fields["mid"] = self.payment_transaction.mid
        return db.run_query(
            lambda: session.query(models.SchemeTransaction).filter(**search_fields).all(),
            session=session,
            read_only=True,
            description="find matching scheme transactions",
        )

    def _find_applicable_scheme_transactions(self, *, session: db.Session):
        return db.run_query(
            lambda: session.query(models.SchemeTransaction).filter(
                models.SchemeTransaction.merchant_identifier_ids.overlap(
                    self.payment_transaction.merchant_identifier_ids
                ),
                models.SchemeTransaction.status == models.TransactionStatus.PENDING,
            ),
            read_only=True,
            session=session,
            description="find pending scheme transactions for matching",
        )

    def _make_spotted_transaction_fields(self):
        merchant_identifier_ids = self.payment_transaction.merchant_identifier_ids

        if len(merchant_identifier_ids) > 1:
            self.log.warning(
                f"More than one MID is present on {self.payment_transaction}! "
                f"MIDs: {merchant_identifier_ids}. "
                "The first MID will be assumed to be the correct one."
            )

        return {
            "merchant_identifier_id": merchant_identifier_ids[0],
            "transaction_id": self.payment_transaction.transaction_id,
            "transaction_date": self.payment_transaction.transaction_date,
            "spend_amount": self.payment_transaction.spend_amount,
            "spend_multiplier": self.payment_transaction.spend_multiplier,
            "spend_currency": self.payment_transaction.spend_currency,
            "card_token": self.payment_transaction.card_token,
            "payment_transaction_id": self.payment_transaction.id,
            "scheme_transaction_id": None,
            "extra_fields": self.payment_transaction.extra_fields,
        }

    def _make_matched_transaction_fields(self, scheme_transaction: models.SchemeTransaction) -> dict:
        matching_merchant_identifier_ids = list(
            set(self.payment_transaction.merchant_identifier_ids).intersection(
                scheme_transaction.merchant_identifier_ids
            )
        )

        if len(matching_merchant_identifier_ids) > 1:
            self.log.warning(
                f"More than one MID is common to {self.payment_transaction} and {scheme_transaction}! "
                f"Matching MIDs: {matching_merchant_identifier_ids}. "
                "The first MID will be assumed to be the correct one."
            )

        st_fields = {
            k: getattr(scheme_transaction, k)
            for k in (
                "transaction_id",
                "transaction_date",
                "spend_amount",
                "spend_multiplier",
                "spend_currency",
                "points_amount",
                "points_multiplier",
            )
        }
        return {
            "merchant_identifier_id": matching_merchant_identifier_ids[0],
            **st_fields,
            "card_token": self.payment_transaction.card_token,
            "payment_transaction_id": self.payment_transaction.id,
            "scheme_transaction_id": scheme_transaction.id,
            "extra_fields": {**self.payment_transaction.extra_fields, **scheme_transaction.extra_fields},
        }

    def match(self, *, session: db.Session) -> t.Optional[MatchResult]:
        if self.payment_transaction.user_identity is None:
            self.log.warning(
                f"Payment transaction {self.payment_transaction} has no user identity, so it cannot be matched."
            )
            return None

        self.log.info(f"Matching {self.payment_transaction}.")
        scheme_transactions = self._find_applicable_scheme_transactions(session=session)
        return self.do_match(scheme_transactions)

    def do_match(self, scheme_transactions) -> t.Optional[MatchResult]:
        raise NotImplementedError("Matching agents must implement the do_match method")

    """
    The main filter recursion method
    Supply a list of filter methods for each payment card provider. If more than one matched transaction is returned
    then the next level of filtering is invoked.
    Params: Scheme transactions, list of filter functions, depth = determines the next filter function to run.
    """

    def _filter(
        self, scheme_transactions: t.List[models.SchemeTransaction], fallback_filter_functions, *, depth: int = 0
    ) -> t.Optional[models.SchemeTransaction]:
        """Recursively filters the transactions based on how many fallback filter functions are available"""
        matched_transaction_count = len(scheme_transactions)

        if matched_transaction_count > 1:
            if depth >= len(fallback_filter_functions):
                return None

            filtered_transactions = fallback_filter_functions[depth](scheme_transactions)
            return self._filter(filtered_transactions, fallback_filter_functions, depth=depth + 1)
        elif matched_transaction_count < 1:
            return None
        else:
            return scheme_transactions[0]

    def _filter_by_time(
        self, scheme_transactions: t.List[models.SchemeTransaction], time_tolerance=60
    ) -> t.List[models.SchemeTransaction]:

        # Temporary - to identify if the payment transaction is settlement or auth
        # settlement transaction_time field cannot be used for filtering as it is inaccurate
        # TODO: This should be removed once payment_transaction.transaction_date
        # is separated into date and time fields
        if self.payment_transaction.extra_fields.get("transaction_time"):
            return scheme_transactions

        transaction_datetime = pendulum.instance(self.payment_transaction.transaction_date)

        min_time = transaction_datetime.subtract(seconds=time_tolerance)
        max_time = transaction_datetime.add(seconds=time_tolerance)
        match_period = pendulum.period(min_time, max_time)

        matched_transactions = [
            transaction
            for transaction in scheme_transactions
            if pendulum.instance(transaction.transaction_date) in match_period
        ]
        return matched_transactions

    def _filter_by_card_number(
        self, scheme_transactions: t.List[models.SchemeTransaction]
    ) -> t.List[models.SchemeTransaction]:
        user_identity = self.payment_transaction.user_identity

        matched_transactions = [
            transaction
            for transaction in scheme_transactions
            if (
                transaction.extra_fields["TransactionCardFirst6"] == user_identity.first_six
                and transaction.extra_fields["TransactionCardLast4"] == user_identity.last_four
            )
        ]
        return matched_transactions

    """
    Auth Codes are 6 digit numbers, possibly not be unique.
    """

    def _filter_by_auth_code(
        self, scheme_transactions: t.List[models.SchemeTransaction]
    ) -> t.List[models.SchemeTransaction]:
        auth_code = self.payment_transaction.auth_code

        if not bool(auth_code and auth_code.strip()):
            return scheme_transactions

        matched_transactions = [
            transaction for transaction in scheme_transactions if transaction.auth_code == auth_code
        ]
        return matched_transactions
