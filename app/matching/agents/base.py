import typing as t
from collections import namedtuple

from app.models import SchemeTransaction, PaymentTransaction
from app.reporting import get_logger
from app.db import Session

session = Session()

MatchResult = namedtuple('MatchResult', 'matched_tx scheme_tx_id')


class BaseMatchingAgent:
    class NoMatchFound(Exception):
        pass

    scheme_slug = None

    def __init__(self, payment_transaction: PaymentTransaction) -> None:
        """Matching agents are expected to query for their own SchemeTransaction objects based on properties of the
        given PaymentTransaction."""
        self.payment_transaction = payment_transaction
        self.log = get_logger(f"matching-agent.{self.scheme_slug}")

    def __repr__(self) -> str:
        return f"{type(self).__name__}(payment_transaction={repr(self.payment_transaction)})"

    def __str__(self) -> str:
        return f"{type(self).__name__}"

    def _get_scheme_transactions(self, **search_fields) -> t.List[SchemeTransaction]:
        search_fields['mid'] = self.payment_transaction.mid
        return session.query(SchemeTransaction).filter(**search_fields)

    def _find_applicable_scheme_transactions(self):
        return session.query(SchemeTransaction).filter(
            SchemeTransaction.merchant_identifier_id == self.payment_transaction.merchant_identifier_id)

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
        return self.do_match(scheme_transactions)

    def do_match(self, scheme_transactions) -> MatchResult:
        raise NotImplementedError('Matching agents must implement the do_match method.')
