import csv
import io
import itertools
import typing as t
from uuid import uuid4

import pendulum

from app.currency import to_pounds
from harness.providers.base import BaseImportDataProvider


def _get_card_scheme(slug: str) -> t.Tuple[int, str]:
    return {
        "amex": (1, "Amex"),
        "visa": (2, "Visa"),
        "mastercard": (3, "MasterCard/MasterCard One"),
        "bink-payment": (9, "Bink-Payment"),
    }[slug]


class Iceland(BaseImportDataProvider):
    def provide(self, fixture: dict) -> bytes:
        transactions = (
            self._build_transaction(transaction, fixture, user["first_six"], user["last_four"])
            for user in fixture["users"]
            for transaction in user.get("transactions", [])
        )

        loyalty_transactions = (
            self._build_transaction(transaction, fixture, transaction["first_six"], transaction["last_four"])
            for transaction in fixture["loyalty_scheme"].get("transactions", [])
        )

        transactions = itertools.chain(transactions, loyalty_transactions)

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            (
                "TransactionCardFirst6",
                "TransactionCardLast4",
                "TransactionCardExpiry",
                "TransactionCardSchemeId",
                "TransactionCardScheme",
                "TransactionStore_Id",
                "TransactionTimestamp",
                "TransactionAmountValue",
                "TransactionAmountUnit",
                "TransactionCashbackValue",
                "TransactionCashbackUnit",
                "TransactionId",
                "TransactionAuthCode",
            )
        )
        writer.writerows(transactions)
        return buf.getvalue().encode()

    @staticmethod
    def _build_transaction(transaction: dict, fixture: dict, first_six: str, last_four: str) -> tuple:
        scheme_id, scheme_name = _get_card_scheme(fixture["payment_provider"]["slug"])
        return (
            first_six,
            last_four,
            "01/80",
            scheme_id,
            scheme_name,
            fixture["mid"],
            pendulum.instance(transaction["date"]).format("YYYY-MM-DD HH:mm:ss"),
            to_pounds(transaction["amount"]),
            "GBP",
            ".00",
            "GBP",
            str(uuid4()),
            transaction["auth_code"],
        )
