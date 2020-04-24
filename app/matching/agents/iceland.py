import typing as t
from datetime import datetime

import pendulum
import sqlalchemy
from sqlalchemy import Date, cast
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from app import models
from app.matching.agents.base import BaseMatchingAgent, MatchResult
from app.service.hermes import PaymentProviderSlug


class Iceland(BaseMatchingAgent):
    def __init__(self, payment_transaction: models.PaymentTransaction) -> None:
        super().__init__(payment_transaction)

        self.fallback_filter_functions = (
            self._filter_by_time,
            self._filter_by_card_number,
        )

        self.time_tolerance = 60  # time tolerance for filtering between time range, in seconds.

    def do_match(self, scheme_transactions: sqlalchemy.orm.query.Query) -> t.Optional[MatchResult]:
        try:
            matcher = {
                PaymentProviderSlug.AMEX: self._base_matcher,
                PaymentProviderSlug.VISA: self._base_matcher,
                PaymentProviderSlug.MASTERCARD: self.mastercard_matcher,
            }[self.payment_transaction.provider_slug]
        except KeyError:
            matcher = self._base_matcher

        return matcher(scheme_transactions)

    def _base_matcher(self, scheme_transactions: sqlalchemy.orm.query.Query) -> t.Optional[MatchResult]:
        """A generic matcher to match on spend_amount, date, and provider_slug fields
        """
        scheme_transactions = scheme_transactions.filter(
            models.SchemeTransaction.spend_amount == self.payment_transaction.spend_amount,
            cast(models.SchemeTransaction.transaction_date, Date)
            == cast(self.payment_transaction.transaction_date, Date),
            models.SchemeTransaction.payment_provider_slug == self.payment_transaction.provider_slug,
        )

        match, multiple_returned = self._check_for_match(scheme_transactions)

        if multiple_returned or not match:
            return None

        return MatchResult(
            matched_transaction=models.MatchedTransaction(
                **self._make_matched_transaction_fields(match), matching_type=models.MatchingType.LOYALTY,
            ),
            scheme_transaction_id=match.id,
        )

    def mastercard_matcher(self, scheme_transactions: sqlalchemy.orm.query.Query) -> t.Optional[MatchResult]:
        scheme_transactions = scheme_transactions.filter(
            models.SchemeTransaction.spend_amount == self.payment_transaction.spend_amount,
            cast(models.SchemeTransaction.transaction_date, Date)
            == cast(self.payment_transaction.transaction_date, Date),
            models.SchemeTransaction.payment_provider_slug == self.payment_transaction.provider_slug,
        )

        match, multiple_returned = self._check_for_match(scheme_transactions)

        if multiple_returned:
            self.filter_level = 0
            match = self._filter(scheme_transactions.all())

        if not match:
            self.log.warning(
                f"Fallback filters failed to match any scheme transactions to payment "
                f"transaction #{self.payment_transaction.id}."
            )
            return None

        return MatchResult(
            matched_transaction=models.MatchedTransaction(
                **self._make_matched_transaction_fields(match), matching_type=models.MatchingType.LOYALTY,
            ),
            scheme_transaction_id=match.id,
        )

    def _check_for_match(
        self, scheme_transactions: sqlalchemy.orm.query.Query
    ) -> t.Tuple[t.Optional[models.SchemeTransaction], bool]:
        match = None
        multiple_returned = False
        try:
            match = scheme_transactions.one()
        except NoResultFound:
            self.log.warning(
                f"Couldn't match any scheme transactions to payment transaction #{self.payment_transaction.id}."
            )
        except MultipleResultsFound:
            self.log.warning(
                f"More than one scheme transaction matches payment transaction #{self.payment_transaction.id}."
            )
            multiple_returned = True

        return match, multiple_returned

    def _filter(
        self, scheme_transactions: t.Sequence[models.SchemeTransaction]
    ) -> t.Optional[t.Union[t.Sequence[models.SchemeTransaction], models.SchemeTransaction]]:
        """Recursively filters the transactions based on how many fallback filter functions are available"""
        matched_transaction_count = len(scheme_transactions)

        if matched_transaction_count > 1:
            if self.filter_level >= len(self.fallback_filter_functions):
                return None

            filtered_transactions = self.fallback_filter_functions[self.filter_level](scheme_transactions)
            self.filter_level += 1
            return self._filter(filtered_transactions)
        elif matched_transaction_count < 1:
            return None
        else:
            return scheme_transactions[0]

    def _filter_by_time(
        self, scheme_transactions: t.Sequence[models.SchemeTransaction]
    ) -> t.List[models.SchemeTransaction]:

        # Temporary - to identify if the payment transaction is settlement or auth
        # settlement transaction_time field cannot be used for filtering as it is inaccurate
        # TODO: This should be removed once payment_transaction.transaction_date
        # is separated into date and time fields
        if self.payment_transaction.extra_fields.get("transaction_time"):
            return scheme_transactions

        transaction_datetime = pendulum.instance(self.payment_transaction.transaction_date)

        min_time = transaction_datetime.subtract(seconds=self.time_tolerance)
        max_time = transaction_datetime.add(seconds=self.time_tolerance)
        match_period = pendulum.period(min_time, max_time)

        matched_transactions = [
            transaction
            for transaction in scheme_transactions
            if pendulum.instance(transaction.transaction_date) in match_period
        ]
        return matched_transactions

    def _filter_by_card_number(
        self, scheme_transactions: t.Iterable[models.SchemeTransaction]
    ) -> t.List[models.SchemeTransaction]:
        user_identity = self.payment_transaction.user_identity

        matched_transactions = [
            transaction
            for transaction in scheme_transactions
            if (
                transaction.extra_fields["TransactionCardFirst6"] == user_identity.first_six
                and transaction.extra_fields["TransactionCardLast4"] == user_identity.last_four
            )
        ]
        return matched_transactions
