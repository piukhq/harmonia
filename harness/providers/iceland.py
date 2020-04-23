import io
import csv
from uuid import uuid4
from random import sample

import pendulum

from harness.providers.base import BaseImportDataProvider
from app.currency import to_pounds
import itertools
from app.service.hermes import hermes


def _get_card_scheme_id(slug: str) -> int:
    return {"amex": 1, "visa": 2, "mastercard-settled": 3, "mastercard-auth": 3, "bink-payment": 6502}[slug]


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
    def _build_transaction(transaction: dict, fixture: dict, first_six: str, last_four: str) -> dict:
        return (
            first_six,
            last_four,
            "01/80",
            _get_card_scheme_id(fixture["payment_provider"]["slug"]),
            hermes.get_payment_provider_slug(fixture["payment_provider"]["slug"]),
            fixture["mid"],
            pendulum.instance(transaction["date"]).format("YYYY-MM-DD HH:mm:ss"),
            to_pounds(transaction["amount"]),
            "GBP",
            ".00",
            "GBP",
            str(uuid4()),
            "".join(str(d) for d in sample(range(0, 10), 6)),
        )
