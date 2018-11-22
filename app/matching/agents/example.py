from app import models
from app.db import Session
from app.matching.agents.base import BaseMatchingAgent, MatchResult

session = Session()


class ExampleMatchingAgent(BaseMatchingAgent):
    scheme_slug = 'aĉetado'

    def _find_applicable_scheme_transactions(self):
        return session.query(models.SchemeTransaction).filter(
            models.SchemeTransaction.merchant_identifier_id == self.payment_transaction.merchant_identifier_id)

    def _fine_match(self, scheme_transactions, fields):
        return scheme_transactions.filter_by(**fields)

    def _make_matched_transaction_fields(self, scheme_transaction):
        st_fields = {
            k: getattr(scheme_transaction, k)
            for k in ('merchant_identifier_id', 'transaction_id', 'transaction_date', 'spend_amount',
                      'spend_multiplier', 'spend_currency', 'points_amount', 'points_multiplier')
        }
        return {
            **st_fields,
            'card_token': self.payment_transaction.card_token,
            'payment_transaction_id': self.payment_transaction.id,
            'scheme_transaction_id': scheme_transaction.id,
            'extra_fields': {
                **self.payment_transaction.extra_fields,
                **scheme_transaction.extra_fields,
            },
        }

    def match(self) -> MatchResult:
        self.log.info(f"Matching {self.payment_transaction}")

        scheme_transactions = self._find_applicable_scheme_transactions()
        scheme_transactions = self._fine_match(scheme_transactions, {
            'spend_amount': self.payment_transaction.spend_amount
        })

        match = scheme_transactions.one()

        return MatchResult(
            matched_tx=models.MatchedTransaction(
                **self._make_matched_transaction_fields(match),
                matching_type=models.MatchingType.LOYALTY,
            ),
            scheme_tx_id=match.id,
        )
