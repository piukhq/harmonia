import typing as t

from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.orm.query import Query

from app import models
from app.matching.agents.base import BaseMatchingAgent, MatchResult


class Iceland(BaseMatchingAgent):
    def _filter_scheme_transactions_with_auth_code(self, scheme_transactions: Query) -> Query:
        scheme_transactions = scheme_transactions.filter(
            models.SchemeTransaction.spend_amount == self.payment_transaction.spend_amount,
            models.SchemeTransaction.payment_provider_slug == self.payment_transaction.provider_slug,
            models.SchemeTransaction.auth_code == self.payment_transaction.auth_code,
        )
        scheme_transactions = self._time_filter(scheme_transactions, tolerance=10)
        return scheme_transactions

    def _filter_scheme_transactions_mastercard(self, scheme_transactions: Query) -> Query:
        scheme_transactions = scheme_transactions.filter(
            models.SchemeTransaction.spend_amount == self.payment_transaction.spend_amount,
            models.SchemeTransaction.payment_provider_slug == self.payment_transaction.provider_slug,
        )
        scheme_transactions = self._time_filter(scheme_transactions, tolerance=60)
        return scheme_transactions

    def _filter_scheme_transactions(self, scheme_transactions: Query):
        return {
            "visa": self._filter_scheme_transactions_with_auth_code,
            "amex": self._filter_scheme_transactions_with_auth_code,
            "mastercard": self._filter_scheme_transactions_mastercard,
        }[self.payment_transaction.provider_slug](scheme_transactions)

    def do_match(self, scheme_transactions: Query) -> t.Optional[MatchResult]:
        scheme_transactions = self._filter_scheme_transactions(scheme_transactions)
        match, multiple_returned = self._check_for_match(scheme_transactions)

        if multiple_returned:
            match = self._filter(scheme_transactions.all(), [self._filter_by_card_number])

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
