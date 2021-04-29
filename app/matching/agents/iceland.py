import typing as t

from sqlalchemy.orm.query import Query

from app import models
from app.matching.agents.base import BaseMatchingAgent, MatchResult


class Iceland(BaseMatchingAgent):
    def _filter_scheme_transactions_with_auth_code(self, scheme_transactions: Query) -> Query:
        scheme_transactions = scheme_transactions.filter(
            models.SchemeTransaction.spend_amount == self.payment_transaction.spend_amount,
            models.SchemeTransaction.payment_provider_slug == self.payment_transaction.provider_slug,
        )

        # auth code is an optional field that we use if we have it
        if self.payment_transaction.auth_code:
            scheme_transactions = scheme_transactions.filter(
                models.SchemeTransaction.auth_code == self.payment_transaction.auth_code
            )

        # apply a 60 second fuzzy match on time
        scheme_transactions = self._time_filter(scheme_transactions, tolerance=60)

        return scheme_transactions

    def _filter_scheme_transactions_amex(self, scheme_transactions: Query) -> Query:
        scheme_transactions = scheme_transactions.filter(
            models.SchemeTransaction.spend_amount == self.payment_transaction.spend_amount,
            models.SchemeTransaction.payment_provider_slug == self.payment_transaction.provider_slug,
        )

        # dpan is an optional field that we use if we have it
        if self.payment_transaction.first_six and self.payment_transaction.last_four:
            scheme_transactions = scheme_transactions.filter(
                models.SchemeTransaction.first_six == self.payment_transaction.first_six,
                models.SchemeTransaction.last_four == self.payment_transaction.last_four,
            )

        # apply a 60 second fuzzy match on time
        scheme_transactions = self._time_filter(scheme_transactions, tolerance=60)

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
            "amex": self._filter_scheme_transactions_amex,
            "mastercard": self._filter_scheme_transactions_mastercard,
        }[self.payment_transaction.provider_slug](scheme_transactions)

    def _filter_by_card_number(
        self, scheme_transactions: t.List[models.SchemeTransaction]
    ) -> t.List[models.SchemeTransaction]:
        user_identity = self.payment_transaction.user_identity

        matched_transactions = [
            transaction
            for transaction in scheme_transactions
            if (transaction.first_six == user_identity.first_six and transaction.last_four == user_identity.last_four)
        ]
        return matched_transactions

    def do_match(self, scheme_transactions: Query) -> t.Optional[MatchResult]:
        scheme_transactions = self._filter_scheme_transactions(scheme_transactions)
        match, multiple_returned = self._check_for_match(scheme_transactions)

        # we only want to filter by card number if the dpan isn't present.
        if multiple_returned and not self.payment_transaction.first_six:
            match = self._filter(scheme_transactions.all(), [self._filter_by_card_number])

        if not match:
            self.log.warning(
                f"Fallback filters failed to match any scheme transactions to payment "
                f"transaction #{self.payment_transaction.id}."
            )
            return None

        return MatchResult(
            matched_transaction=models.MatchedTransaction(
                **self.make_matched_transaction_fields(match),
                matching_type=models.MatchingType.LOYALTY,
            ),
            scheme_transaction_id=match.id,
        )
