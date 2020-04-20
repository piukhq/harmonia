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

    def _get_scheme_transactions(self, *, session: db.Session, **search_fields) -> t.List[models.SchemeTransaction]:
        search_fields["mid"] = self.payment_transaction.mid
        return db.run_query(
            lambda: session.query(models.SchemeTransaction).filter(**search_fields).all(),
            session=session,
            read_only=True,
            description="find matching scheme transactions",
        )

    def _find_applicable_scheme_transactions(self, *, session: db.Session):
        return db.run_query(
            lambda: session.query(models.SchemeTransaction).filter(
                models.SchemeTransaction.merchant_identifier_ids.overlap(
                    self.payment_transaction.merchant_identifier_ids
                ),
                models.SchemeTransaction.status == models.TransactionStatus.PENDING,
            ),
            read_only=True,
            session=session,
            description="find pending scheme transactions for matching",
        )

    def _make_spotted_transaction_fields(self):
        merchant_identifier_ids = self.payment_transaction.merchant_identifier_ids

        if len(merchant_identifier_ids) > 1:
            self.log.warning(
                f"More than one MID is present on {self.payment_transaction}! "
                f"MIDs: {merchant_identifier_ids}. "
                "The first MID will be assumed to be the correct one."
            )

        return {
            "merchant_identifier_id": merchant_identifier_ids[0],
            "transaction_id": self.payment_transaction.transaction_id,
            "transaction_date": self.payment_transaction.transaction_date,
            "spend_amount": self.payment_transaction.spend_amount,
            "spend_multiplier": self.payment_transaction.spend_multiplier,
            "spend_currency": self.payment_transaction.spend_currency,
            "card_token": self.payment_transaction.card_token,
            "payment_transaction_id": self.payment_transaction.id,
            "scheme_transaction_id": None,
            "extra_fields": self.payment_transaction.extra_fields,
        }

    def _make_matched_transaction_fields(self, scheme_transaction: models.SchemeTransaction) -> dict:
        matching_merchant_identifier_ids = list(
            set(self.payment_transaction.merchant_identifier_ids).intersection(
                scheme_transaction.merchant_identifier_ids
            )
        )

        if len(matching_merchant_identifier_ids) > 1:
            self.log.warning(
                f"More than one MID is common to {self.payment_transaction} and {scheme_transaction}! "
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

    def match(self, *, session: db.Session) -> t.Optional[MatchResult]:
        if self.payment_transaction.user_identity is None:
            self.log.warning(
                f"Payment transaction {self.payment_transaction} has no user identity, so it cannot be matched."
            )
            return None

        self.log.info(f"Matching {self.payment_transaction}.")
        scheme_transactions = self._find_applicable_scheme_transactions(session=session)
        return self.do_match(scheme_transactions)

    def do_match(self, scheme_transactions) -> t.Optional[MatchResult]:
        raise NotImplementedError("Matching agents must implement the do_match method")
