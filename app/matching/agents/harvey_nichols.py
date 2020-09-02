import typing as t

from sqlalchemy.orm.query import Query

from app import models
from app.matching.agents.base import BaseMatchingAgent, MatchResult


class HarveyNichols(BaseMatchingAgent):
    def _filter_scheme_transactions_with_time(self, scheme_transactions: Query) -> Query:
        scheme_transactions = scheme_transactions.filter(
            models.SchemeTransaction.spend_amount == self.payment_transaction.spend_amount,
            models.SchemeTransaction.payment_provider_slug == self.payment_transaction.provider_slug,
        )
        scheme_transactions = self._time_filter(scheme_transactions, tolerance=30)
        return scheme_transactions

    def _filter_scheme_transactions_mastercard(self, scheme_transactions: Query) -> Query:
        scheme_transactions = scheme_transactions.filter(
            models.SchemeTransaction.spend_amount == self.payment_transaction.spend_amount,
            models.SchemeTransaction.payment_provider_slug == self.payment_transaction.provider_slug,
        )
        scheme_transactions = self._time_filter(scheme_transactions, tolerance=60)
        return scheme_transactions

    def _filter_scheme_transactions(self, scheme_transactions: Query) -> Query:
        return {
            "visa": self._filter_scheme_transactions_with_time,
            "amex": self._filter_scheme_transactions_with_time,
            "mastercard": self._filter_scheme_transactions_mastercard,
            # for end to end testing
            "bink-payment": self._filter_scheme_transactions_with_time,
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
                **self._make_matched_transaction_fields(match), matching_type=models.MatchingType.LOYALTY
            ),
            scheme_transaction_id=match.id,
        )

    def _filter_by_card_number(
        self, scheme_transactions: t.List[models.SchemeTransaction]
    ) -> t.List[models.SchemeTransaction]:
        user_identity = self.payment_transaction.user_identity

        matched_transactions = [
            transaction
            for transaction in scheme_transactions
            if (
                transaction.extra_fields["card"]["last_4"] == user_identity.last_four
                and (
                    transaction.extra_fields["card"]["first_6"] == user_identity.first_six
                    or transaction.extra_fields["card"]["first_6"] == "000000"
                )
            )
        ]
        return matched_transactions
