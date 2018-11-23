from app import models
from app.db import Session
from app.matching.agents.base import BaseMatchingAgent, MatchResult

session = Session()


class ExampleMatchingAgent(BaseMatchingAgent):
    scheme_slug = 'aĉetado'

    def do_match(self, scheme_transactions) -> MatchResult:
        scheme_transactions = self._fine_match(scheme_transactions,
                                               {'spend_amount': self.payment_transaction.spend_amount})

        match = scheme_transactions.one()

        return MatchResult(
            matched_tx=models.MatchedTransaction(
                **self._make_matched_transaction_fields(match),
                matching_type=models.MatchingType.LOYALTY,
            ),
            scheme_tx_id=match.id,
        )
