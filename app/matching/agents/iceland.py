import typing as t
import sqlalchemy
from sqlalchemy import Date, cast
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from app import models
from app.matching.agents.base import BaseMatchingAgent, MatchResult


class Iceland(BaseMatchingAgent):
    def __init__(self, payment_transaction: models.PaymentTransaction) -> None:
        super().__init__(payment_transaction)

    def filter_functions(self, payment_slug: str) -> tuple:
        return {
            "amex": (self._filter_by_auth_code, lambda tx: self._filter_by_time(tx, time_tolerance=10)),
            "mastercard": (lambda tx: self._filter_by_time(tx, time_tolerance=60), self._filter_by_card_number),
            "visa": (self._filter_by_auth_code, lambda tx: self._filter_by_time(tx, time_tolerance=10)),
        }[payment_slug]

    def do_match(self, scheme_transactions: sqlalchemy.orm.query.Query) -> t.Optional[MatchResult]:
        scheme_transactions = scheme_transactions.filter(
            models.SchemeTransaction.spend_amount == self.payment_transaction.spend_amount,
            cast(models.SchemeTransaction.transaction_date, Date)
            == cast(self.payment_transaction.transaction_date, Date),
            models.SchemeTransaction.payment_provider_slug == self.payment_transaction.provider_slug,
        )

        match, multiple_returned = self._check_for_match(scheme_transactions)

        if multiple_returned:
            match = self._filter(
                scheme_transactions.all(), self.filter_functions(self.payment_transaction.provider_slug)
            )

        if not match:
            self.log.warning(
                f"Fallback filters failed to match any scheme transactions to payment "
                f"transaction #{self.payment_transaction.id}."
            )
            return None

        return MatchResult(
            matched_transaction=models.MatchedTransaction(
                **self._make_matched_transaction_fields(match), matching_type=models.MatchingType.LOYALTY,
            ),
            scheme_transaction_id=match.id,
        )

    def _check_for_match(
        self, scheme_transactions: sqlalchemy.orm.query.Query
    ) -> t.Tuple[t.Optional[models.SchemeTransaction], bool]:
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
