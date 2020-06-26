import typing as t

from app import models
from app.matching.agents.base import BaseMatchingAgent, MatchResult
from sqlalchemy.orm.query import Query


class WhSmith(BaseMatchingAgent):
    def _filter_scheme_transactions(self, scheme_transactions: Query) -> Query:
        scheme_transactions = scheme_transactions.filter(
            models.SchemeTransaction.spend_amount == self.payment_transaction.spend_amount,
            models.SchemeTransaction.payment_provider_slug == self.payment_transaction.provider_slug,
        )
        if self.payment_transaction.provider_slug != "mastercard":
            scheme_transactions = scheme_transactions.filter(
                models.SchemeTransaction.auth_code == self.payment_transaction.auth_code
            )
        scheme_transactions = self._time_filter(scheme_transactions, tolerance=10)
        return scheme_transactions

    def _filter_by_last_four(self, scheme_transactions: Query) -> Query:
        user_identity = self.payment_transaction.user_identity

        matched_transactions = [
            transaction
            for transaction in scheme_transactions
            if transaction.extra_fields["last_four"] == user_identity.last_four
        ]
        return matched_transactions

    def do_match(self, scheme_transactions: Query) -> t.Optional[MatchResult]:
        scheme_transactions = self._filter_scheme_transactions(scheme_transactions)
        match, multiple_returned = self._check_for_match(scheme_transactions)

        if multiple_returned:
            match = self._filter(scheme_transactions.all(), [self._filter_by_last_four])

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
