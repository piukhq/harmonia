import typing as t

from app import models
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from app.matching.agents.base import BaseMatchingAgent, MatchResult


class Cooperative(BaseMatchingAgent):
    def do_match(self, scheme_transactions) -> t.Optional[MatchResult]:
        scheme_transactions = scheme_transactions.filter_by(
            merchant_identifier_ids=self.payment_transaction.merchant_identifier_ids,
            transaction_date=self.payment_transaction.transaction_date,
            spend_amount=self.payment_transaction.spend_amount,
            spend_currency=self.payment_transaction.spend_currency,
            spend_multiplier=self.payment_transaction.spend_multiplier,
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
            matched_transaction=models.MatchedTransaction(
                **self._make_matched_transaction_fields(match), matching_type=models.MatchingType.LOYALTY
            ),
            scheme_transaction_id=match.id,
        )
