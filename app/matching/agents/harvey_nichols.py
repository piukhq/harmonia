import typing as t
import pendulum

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import orm
from app import models
from app.matching.agents.base import BaseMatchingAgent, MatchResult


class HarveyNichols(BaseMatchingAgent):

    def filter_functions(self, payment_slug: str) -> tuple:
        return {
            "amex": (self._filter_by_card_number, ),
            "mastercard": (self._filter_by_card_number, ),
            "visa": (self._filter_by_card_number, ),
        }[payment_slug]

    def _time_filter(
        self, scheme_transactions: orm.query.Query, *, tolerance: int
    ) -> orm.query.Query:
        if self.payment_transaction.has_time:
            transaction_date = pendulum.instance(self.payment_transaction.transaction_date)
            return scheme_transactions.filter(
                models.SchemeTransaction.transaction_date.between(
                    transaction_date.subtract(seconds=tolerance).isoformat(),
                    transaction_date.add(seconds=tolerance).isoformat(),
                )
            )
        return scheme_transactions

    def _filter_scheme_transactions_with_time(
        self, scheme_transactions: orm.query.Query
    ) -> orm.query.Query:
        scheme_transactions = scheme_transactions.filter(
            models.SchemeTransaction.spend_amount == self.payment_transaction.spend_amount,
            models.SchemeTransaction.payment_provider_slug == self.payment_transaction.provider_slug,
        )
        scheme_transactions = self._time_filter(scheme_transactions, tolerance=10)
        return scheme_transactions

    def _filter_scheme_transactions_mastercard(
        self, scheme_transactions: orm.query.Query
    ) -> orm.query.Query:
        scheme_transactions = scheme_transactions.filter(
            models.SchemeTransaction.spend_amount == self.payment_transaction.spend_amount,
            models.SchemeTransaction.payment_provider_slug == self.payment_transaction.provider_slug,
        )
        scheme_transactions = self._time_filter(scheme_transactions, tolerance=60)
        return scheme_transactions

    def _filter_scheme_transactions(self, scheme_transactions: orm.query.Query):
        return {
            "visa": self._filter_scheme_transactions_with_time,
            "amex": self._filter_scheme_transactions_with_time,
            "mastercard": self._filter_scheme_transactions_mastercard,
        }[self.payment_transaction.provider_slug](scheme_transactions)

    # TODO: scheme_transactions should be a query... not sure what type hint that needs
    def do_match(self, scheme_transactions: orm.query.Query) -> t.Optional[MatchResult]:
        scheme_transactions = self._filter_scheme_transactions(scheme_transactions)

        match, multiple_returned = self._check_for_match(scheme_transactions)

        if multiple_returned:
            match = self._filter(
                scheme_transactions.all(), self.filter_functions(self.payment_transaction.provider_slug)
            )

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

    def _check_for_match(
        self, scheme_transactions: orm.query.Query
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

    def _filter_by_card_number(
        self, scheme_transactions: t.List[models.SchemeTransaction]
    ) -> t.List[models.SchemeTransaction]:
        user_identity = self.payment_transaction.user_identity

        matched_transactions = [
            transaction
            for transaction in scheme_transactions
            if (transaction.extra_fields["card"]["last_4"] == user_identity.last_four
                and (transaction.extra_fields["card"]["first_6"] == user_identity.first_six
                     or transaction.extra_fields["card"]["first_6"] == "000000"
                     )
                )
        ]
        return matched_transactions
