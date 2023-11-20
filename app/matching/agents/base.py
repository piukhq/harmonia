import typing as t
from enum import Enum

import pendulum
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.orm.query import Query

from app import db, models
from app.reporting import get_logger


class MatchResult(t.NamedTuple):
    matched_transaction: models.MatchedTransaction
    user_identity: models.UserIdentity
    scheme_transaction_id: t.Optional[int]


class TimestampPrecision(Enum):
    AUTO = "auto"
    MINUTES = "minutes"


class BaseMatchingAgent:
    class NoMatchFound(Exception):
        pass

    def __init__(self, payment_transaction: models.PaymentTransaction, user_identity: models.UserIdentity) -> None:
        """Matching agents are expected to query for their own SchemeTransaction objects based on properties of the
        given payment transaction."""
        self.payment_transaction = payment_transaction
        self.user_identity = user_identity
        self.log = get_logger(f"matching-agent.{type(self).__name__}")

    def __repr__(self) -> str:
        return f"{type(self).__name__}(payment_transaction={repr(self.payment_transaction)})"

    def __str__(self) -> str:
        return f"{type(self).__name__}"

    def _time_filter(
        self,
        scheme_transactions: Query,
        *,
        tolerance: int,
        scheme_timestamp_precision: TimestampPrecision = TimestampPrecision.AUTO,
    ) -> Query:
        transaction_date = pendulum.instance(self.payment_transaction.transaction_date)

        if self.payment_transaction.has_time:
            return scheme_transactions.filter(
                models.SchemeTransaction.transaction_date.between(
                    transaction_date.subtract(seconds=tolerance).isoformat(timespec=scheme_timestamp_precision.value),
                    transaction_date.add(seconds=tolerance).isoformat(timespec=scheme_timestamp_precision.value),
                )
            )
        else:
            # checking a day's range like this means that transactions very close to midnight may not match.
            # this risk is known & accepted at the time of writing.
            return scheme_transactions.filter(
                models.SchemeTransaction.transaction_date.between(
                    transaction_date.date().isoformat(),
                    transaction_date.add(days=1).date().isoformat(),
                )
            )

    def _get_scheme_transactions(self, *, session: db.Session, **search_fields) -> t.List[models.SchemeTransaction]:
        search_fields["mid"] = self.payment_transaction.mid
        return db.run_query(
            lambda: session.query(models.SchemeTransaction).filter(**search_fields).all(),
            session=session,
            read_only=True,
            description="find matching scheme transactions",
        )

    def _find_applicable_scheme_transactions(self, *, session: db.Session):
        since = pendulum.now().date().add(days=-14)
        return db.run_query(
            lambda: session.query(models.SchemeTransaction).filter(
                models.SchemeTransaction.mids.any(self.payment_transaction.mid),
                models.SchemeTransaction.status == models.TransactionStatus.PENDING,
                models.SchemeTransaction.created_at >= since.isoformat(),
                models.SchemeTransaction.spend_amount == self.payment_transaction.spend_amount,
            ),
            read_only=True,
            session=session,
            description="find pending scheme transactions for matching",
        )

    def make_spotted_transaction_fields(self):
        return {
            "merchant_identifier_id": self.payment_transaction.merchant_identifier_ids[0],
            "mid": self.payment_transaction.mid,
            "transaction_id": self.payment_transaction.transaction_id,
            "transaction_date": self.payment_transaction.transaction_date,
            "spend_amount": self.payment_transaction.spend_amount,
            "spend_multiplier": self.payment_transaction.spend_multiplier,
            "spend_currency": self.payment_transaction.spend_currency,
            "card_token": self.payment_transaction.card_token,
            "extra_fields": self.payment_transaction.extra_fields,
        }

    def make_matched_transaction_fields(self, scheme_transaction: models.SchemeTransaction) -> dict:
        st_fields = {
            k: getattr(scheme_transaction, k)
            for k in (
                "transaction_id",
                "transaction_date",
                "spend_amount",
                "spend_multiplier",
                "spend_currency",
            )
        }
        return {
            "merchant_identifier_id": self.payment_transaction.merchant_identifier_ids[0],
            "mid": self.payment_transaction.mid,
            **st_fields,
            "card_token": self.payment_transaction.card_token,
            "extra_fields": {
                **(self.payment_transaction.extra_fields or {}),
                **(scheme_transaction.extra_fields or {}),
            },
        }

    def match(self, *, session: db.Session) -> t.Optional[MatchResult]:
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

    def _check_for_match(self, scheme_transactions: Query) -> t.Tuple[t.Optional[models.SchemeTransaction], bool]:
        match = None
        multiple_returned = False
        try:
            match = scheme_transactions.one()
        except NoResultFound:
            self.log.warning(
                f"Couldn't match any scheme transactions to payment transaction #{self.payment_transaction.id}."
            )
        except MultipleResultsFound:
            self.log.warning(
                f"More than one scheme transaction matches payment transaction #{self.payment_transaction.id}."
            )
            multiple_returned = True

        return match, multiple_returned
