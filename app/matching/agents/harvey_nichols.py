import typing as t

import pendulum
from sqlalchemy.orm.query import Query

from app import models
from app.matching.agents.base import BaseMatchingAgent, MatchResult


class HarveyNichols(BaseMatchingAgent):
    @property
    def time_tolerance(self):
        return 60 if self.payment_transaction.provider_slug == "mastercard" else 30

    def _filter_scheme_transactions_with_auth_code(self, scheme_transactions: Query) -> Query:
        transaction_date = pendulum.instance(self.payment_transaction.transaction_date)
        scheme_transactions = scheme_transactions.filter(
            models.SchemeTransaction.spend_amount == self.payment_transaction.spend_amount,
            models.SchemeTransaction.payment_provider_slug == self.payment_transaction.provider_slug,
        )
        if self.payment_transaction.auth_code:
            scheme_transactions = scheme_transactions.filter(
                models.SchemeTransaction.auth_code == self.payment_transaction.auth_code,
                models.SchemeTransaction.transaction_date.between(
                    transaction_date.date().isoformat(),
                    transaction_date.add(days=1).date().isoformat(),
                ),
            )
        else:
            scheme_transactions = self._time_filter(scheme_transactions, tolerance=self.time_tolerance)

        return scheme_transactions

    def _filter_scheme_transactions_with_dpan(self, scheme_transactions: Query) -> Query:
        scheme_transactions = scheme_transactions.filter(
            models.SchemeTransaction.spend_amount == self.payment_transaction.spend_amount,
            models.SchemeTransaction.payment_provider_slug == self.payment_transaction.provider_slug,
        )

        # dpan is an optional field that we use if we have it
        if self.payment_transaction.first_six and self.payment_transaction.last_four:
            scheme_transactions = scheme_transactions.filter(
                models.SchemeTransaction.first_six.in_([self.payment_transaction.first_six, "000000"]),
                models.SchemeTransaction.last_four == self.payment_transaction.last_four,
            )

        scheme_transactions = self._time_filter(scheme_transactions, tolerance=self.time_tolerance)
        return scheme_transactions

    def _filter_scheme_transactions(self, scheme_transactions: Query) -> Query:
        return {
            "visa": self._filter_scheme_transactions_with_auth_code,
            "amex": self._filter_scheme_transactions_with_dpan,
            "mastercard": self._filter_scheme_transactions_with_auth_code,
        }[self.payment_transaction.provider_slug](scheme_transactions)

    def do_match(self, scheme_transactions: Query) -> t.Optional[MatchResult]:
        scheme_transactions = self._filter_scheme_transactions(scheme_transactions)

        match, multiple_returned = self._check_for_match(scheme_transactions)

        # we only want to filter by card number if the dpan isn't present.
        if multiple_returned and not self.payment_transaction.first_six:
            match = self._filter(scheme_transactions.all(), [self._filter_by_time, self._filter_by_card_number])

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
            user_identity=self.user_identity,
            scheme_transaction_id=match.id,
        )

    def _filter_by_card_number(
        self, scheme_transactions: t.List[models.SchemeTransaction]
    ) -> t.List[models.SchemeTransaction]:
        matched_transactions = [
            transaction
            for transaction in scheme_transactions
            if (
                transaction.last_four == self.user_identity.last_four
                and (transaction.first_six == self.user_identity.first_six or transaction.first_six == "000000")
            )
        ]
        return matched_transactions

    def _filter_by_time(
        self, scheme_transactions: t.List[models.SchemeTransaction]
    ) -> t.List[models.SchemeTransaction]:
        date = pendulum.instance(self.payment_transaction.transaction_date)
        before = date.subtract(seconds=self.time_tolerance)
        after = date.add(seconds=self.time_tolerance)
        matched_transactions = [
            transaction for transaction in scheme_transactions if before <= transaction.transaction_date <= after
        ]
        return matched_transactions
