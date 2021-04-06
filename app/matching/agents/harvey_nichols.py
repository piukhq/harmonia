import typing as t

from sqlalchemy.orm.query import Query
import pendulum

from app import models
from app.matching.agents.base import BaseMatchingAgent, MatchResult


class HarveyNichols(BaseMatchingAgent):
    def _filter_scheme_transactions_with_auth_code(self, scheme_transactions: Query) -> Query:
        scheme_transactions = scheme_transactions.filter(
            models.SchemeTransaction.spend_amount == self.payment_transaction.spend_amount,
            models.SchemeTransaction.payment_provider_slug == self.payment_transaction.provider_slug,
        )
        if self.payment_transaction.auth_code:
            scheme_transactions = scheme_transactions.filter(
                models.SchemeTransaction.auth_code == self.payment_transaction.auth_code
            )
        return scheme_transactions

    def _filter_scheme_transactions_with_time(self, scheme_transactions: Query) -> Query:
        scheme_transactions = scheme_transactions.filter(
            models.SchemeTransaction.spend_amount == self.payment_transaction.spend_amount,
            models.SchemeTransaction.payment_provider_slug == self.payment_transaction.provider_slug,
        )
        scheme_transactions = self._time_filter(scheme_transactions, tolerance=30)
        return scheme_transactions

    def _filter_scheme_transactions(self, scheme_transactions: Query) -> Query:
        return {
            "visa": self._filter_scheme_transactions_with_auth_code,
            "amex": self._filter_scheme_transactions_with_time,
            "mastercard": self._filter_scheme_transactions_with_time,
            # for end to end testing
            "bink-payment": self._filter_scheme_transactions_with_time,
        }[self.payment_transaction.provider_slug](scheme_transactions)

    def do_match(self, scheme_transactions: Query) -> t.Optional[MatchResult]:
        scheme_transactions = self._filter_scheme_transactions(scheme_transactions)

        match, multiple_returned = self._check_for_match(scheme_transactions)

        if multiple_returned:
            match = self._filter(scheme_transactions.all(), [self._filter_by_time, self._filter_by_card_number])

        if not match:
            self.log.warning(
                f"Fallback filters failed to match any scheme transactions to payment "
                f"transaction #{self.payment_transaction.id}."
            )
            return None

        return MatchResult(
            matched_transaction=models.MatchedTransaction(
                **self.make_matched_transaction_fields(match), matching_type=models.MatchingType.LOYALTY
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

    def _filter_by_time(
        self, scheme_transactions: t.List[models.SchemeTransaction]
    ) -> t.List[models.SchemeTransaction]:
        date = pendulum.instance(self.payment_transaction.transaction_date)
        before = date.subtract(seconds=30)
        after = date.add(seconds=30)
        matched_transactions = [
            transaction for transaction in scheme_transactions if before <= transaction.transaction_date <= after
        ]
        return matched_transactions
