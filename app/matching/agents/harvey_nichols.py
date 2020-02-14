import typing as t

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from app import models
from app.matching.agents.base import BaseMatchingAgent, MatchResult


class HarveyNichols(BaseMatchingAgent):
    # TODO: scheme_transactions should be a query... not sure what type hint that needs
    def do_match(self, scheme_transactions) -> t.Optional[MatchResult]:
        user_identity = self.payment_transaction.user_identity
        scheme_transactions = scheme_transactions.filter(
            models.SchemeTransaction.spend_amount == self.payment_transaction.spend_amount,
            models.SchemeTransaction.extra_fields["card"]["first_6"].astext == user_identity.first_six,
            models.SchemeTransaction.extra_fields["card"]["last_4"].astext == user_identity.last_four,
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
