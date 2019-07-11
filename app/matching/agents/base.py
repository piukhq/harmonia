import typing as t
from collections import namedtuple

from app.reporting import get_logger
from app import models, db

MatchResult = namedtuple("MatchResult", ("matched_transaction", "scheme_transaction_id"))


class BaseMatchingAgent:
    class NoMatchFound(Exception):
        pass

    def __init__(self, payment_transaction: models.PaymentTransaction) -> None:
        """Matching agents are expected to query for their own SchemeTransaction objects based on properties of the
        given payment transaction."""
        self.payment_transaction = payment_transaction
        self.log = get_logger(f"matching-agent.{type(self).__name__}")

    def __repr__(self) -> str:
        return f"{type(self).__name__}(payment_transaction={repr(self.payment_transaction)})"

    def __str__(self) -> str:
        return f"{type(self).__name__}"

    def _get_scheme_transactions(self, **search_fields) -> t.List[models.SchemeTransaction]:
        search_fields["mid"] = self.payment_transaction.mid
        return db.run_query(lambda: db.session.query(models.SchemeTransaction).filter(**search_fields))

    def _find_applicable_scheme_transactions(self):
        return db.run_query(
            lambda: db.session.query(models.SchemeTransaction).filter(
                models.SchemeTransaction.merchant_identifier_ids.overlap(
                    self.payment_transaction.merchant_identifier_ids
                ),
                models.SchemeTransaction.status == models.TransactionStatus.PENDING,
            )
        )

    def _fine_match(self, scheme_transactions, fields):
        return scheme_transactions.filter_by(**fields)

    def _make_matched_transaction_fields(self, scheme_transaction: models.SchemeTransaction) -> dict:
        matching_merchant_identifier_ids = list(
            set(self.payment_transaction.merchant_identifier_ids).intersection(
                scheme_transaction.merchant_identifier_ids
            )
        )

        if len(matching_merchant_identifier_ids) > 1:
            self.log.warning(
                f"More than one MIDs are common to {self.payment_transaction} and {scheme_transaction}! "
                f"Matching MIDs: {matching_merchant_identifier_ids}. "
                "The first MID will be assumed to be the correct one."
            )

        st_fields = {
            k: getattr(scheme_transaction, k)
            for k in (
                "transaction_id",
                "transaction_date",
                "spend_amount",
                "spend_multiplier",
                "spend_currency",
                "points_amount",
                "points_multiplier",
            )
        }
        return {
            "merchant_identifier_id": matching_merchant_identifier_ids[0],
            **st_fields,
            "card_token": self.payment_transaction.card_token,
            "payment_transaction_id": self.payment_transaction.id,
            "scheme_transaction_id": scheme_transaction.id,
            "extra_fields": {**self.payment_transaction.extra_fields, **scheme_transaction.extra_fields},
        }

    def match(self) -> t.Optional[MatchResult]:
        self.log.info(f"Matching {self.payment_transaction}.")
        scheme_transactions = self._find_applicable_scheme_transactions()
        return self.do_match(scheme_transactions)

    def do_match(self, scheme_transactions) -> t.Optional[MatchResult]:
        raise NotImplementedError("Matching agents must implement the do_match method")
