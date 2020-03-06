import io
import csv
from uuid import uuid4
from random import sample

import pendulum

from harness.providers.base import BaseImportDataProvider


def _get_card_scheme_id(slug: str) -> int:
    return {"amex": 1, "visa": 2, "mastercard": 3, "bink-payment": 6502}[slug]


class Iceland(BaseImportDataProvider):
    def provide(self, fixture: dict) -> bytes:
        transactions = (
            (
                user["first_six"],
                user["last_four"],
                "01/80",
                _get_card_scheme_id(fixture["payment_provider"]["slug"]),
                fixture["payment_provider"]["slug"].title(),
                fixture["mid"],
                pendulum.instance(transaction["date"]).format("YYYY-MM-DD hh:mm:ss"),
                transaction["amount"] / 100,
                "GBP",
                ".00",
                "GBP",
                str(uuid4()),
                "".join(str(d) for d in sample(range(0, 10), 6)),
            )
            for user in fixture["users"]
            for transaction in user["transactions"]
        )

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
