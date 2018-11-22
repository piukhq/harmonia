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

    def match(self) -> MatchResult:
        raise NotImplementedError('Matching agents must override the match() method.')
