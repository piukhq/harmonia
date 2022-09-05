import typing as t

from app import models
from app.matching.agents.base import BaseMatchingAgent, MatchResult


class GenericLoyalty(BaseMatchingAgent):
    def do_match(self, scheme_transactions, primary_identifier) -> t.Optional[MatchResult]:
        scheme_transactions = scheme_transactions.filter(
            models.SchemeTransaction.spend_amount == self.payment_transaction.spend_amount
        )
        match, multiple_returned = self._check_for_match(scheme_transactions)
        if not match or multiple_returned:
            return None

        return MatchResult(
            matched_transaction=models.MatchedTransaction(
                **self.make_matched_transaction_fields(match, primary_identifier),
                matching_type=models.MatchingType.LOYALTY
            ),
            user_identity=self.user_identity,
            scheme_transaction_id=match.id,
        )
