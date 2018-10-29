import typing as t

from app.models import SchemeTransaction, PaymentTransaction, MatchedTransaction
from app.reporting import get_logger
from app.db import Session

session = Session()
log = get_logger('match-agent')


class BaseMatchingAgent:
    class NoMatchFound(Exception):
        pass

    def __init__(self, payment_transaction: PaymentTransaction) -> None:
        """Matching agents are expected to query for their own SchemeTransaction objects based on properties of the
        given PaymentTransaction."""
        self.payment_transaction = payment_transaction

    def _get_scheme_transactions(self, **search_fields) -> t.List[SchemeTransaction]:
        search_fields['mid'] = self.payment_transaction.mid
        return session.query(SchemeTransaction).filter(**search_fields)

    def match(self) -> MatchedTransaction:
        raise NotImplementedError('Matching agents must override the match() method.')
