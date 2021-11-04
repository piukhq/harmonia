import typing as t
from datetime import datetime, time

import pendulum
from sqlalchemy.orm.query import Query

from app import models
from app.matching.agents.base import BaseMatchingAgent, MatchResult


class Wasabi(BaseMatchingAgent):
    time_tolerance = 60 * 3

    def _query_by_auth_code(self, scheme_transactions: Query) -> t.Optional[models.SchemeTransaction]:
        """
        * Query: Scheme + MID + Date + Amount + (Auth Code | Time)
        * Fallback: Time, PAN F6L4
        """
        scheme_transactions = scheme_transactions.filter(
            models.SchemeTransaction.payment_provider_slug == self.payment_transaction.provider_slug,
            models.SchemeTransaction.spend_amount == self.payment_transaction.spend_amount,
        )

        if self.payment_transaction.auth_code:
            scheme_transactions = scheme_transactions.filter(
                models.SchemeTransaction.auth_code == self.payment_transaction.auth_code,
                models.SchemeTransaction.transaction_date.between(
                    *(
                        datetime.combine(self.payment_transaction.transaction_date.date(), time_parts).isoformat()
                        for time_parts in (time.min, time.max)
                    )
                ),
            )
        else:
            scheme_transactions = self._time_filter(scheme_transactions, tolerance=self.time_tolerance)

        match, multiple_returned = self._check_for_match(scheme_transactions)

        if multiple_returned:
            match = self._filter(scheme_transactions.all(), [self._filter_by_time, self._filter_by_card_number])

        return match

    def _query_by_dpan(self, scheme_transactions: Query) -> t.Optional[models.SchemeTransaction]:
        """
        * Query: Scheme + MID + Date + Amount + Time + [PAN F6L4]
        * Fallback: PAN F6L4 (if no DPAN)
        """
        scheme_transactions = scheme_transactions.filter(
            models.SchemeTransaction.payment_provider_slug == self.payment_transaction.provider_slug,
            models.SchemeTransaction.spend_amount == self.payment_transaction.spend_amount,
        )
        scheme_transactions = self._time_filter(scheme_transactions, tolerance=self.time_tolerance)

        # dpan is an optional field that we use if we have it
        if self.payment_transaction.first_six:
            scheme_transactions = scheme_transactions.filter(
                models.SchemeTransaction.first_six == self.payment_transaction.first_six,
                models.SchemeTransaction.last_four == self.payment_transaction.last_four,
            )

        match, multiple_returned = self._check_for_match(scheme_transactions)

        # we only apply fallback filters if we didn't get dpan
        if multiple_returned and not self.payment_transaction.first_six:
            match = self._filter(scheme_transactions.all(), [self._filter_by_card_number])

        return match

    def _filter_scheme_transactions(self, scheme_transactions: Query) -> t.Optional[models.SchemeTransaction]:
        return {"visa": self._query_by_auth_code, "amex": self._query_by_dpan, "mastercard": self._query_by_auth_code}[
            self.payment_transaction.provider_slug
        ](scheme_transactions)

    def _filter_by_card_number(
        self, scheme_transactions: t.List[models.SchemeTransaction]
    ) -> t.List[models.SchemeTransaction]:
        matched_transactions = [
            transaction
            for transaction in scheme_transactions
            if (
                transaction.first_six == self.user_identity.first_six
                and transaction.last_four == self.user_identity.last_four
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

    def do_match(self, scheme_transactions: Query) -> t.Optional[MatchResult]:
        match = self._filter_scheme_transactions(scheme_transactions)

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
