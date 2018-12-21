import typing as t

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from app import models
from app.matching.agents.base import BaseMatchingAgent, MatchResult


class ExampleMatchingAgent(BaseMatchingAgent):
    scheme_slug = "aĉetado"

    def do_match(self, scheme_transactions) -> t.Optional[MatchResult]:
        scheme_transactions = self._fine_match(
            scheme_transactions,
            {
                "spend_amount": self.payment_transaction.spend_amount,
                "transaction_date": self.payment_transaction.transaction_date,
            },
        )

        try:
            match = scheme_transactions.one()
        except NoResultFound:
            self.log.warning(
                f"Couldn't match any scheme transactions to payment transaction #{self.payment_transaction.id}."
            )
            return None
        except MultipleResultsFound:
            self.log.warning(
                f"More than one scheme transaction matches payment transaction #{self.payment_transaction.id}."
            )
            return None

        return MatchResult(
            matched_tx=models.MatchedTransaction(
                **self._make_matched_transaction_fields(match),
                matching_type=models.MatchingType.LOYALTY,
            ),
            scheme_tx_id=match.id,
        )
