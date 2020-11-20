import csv
import io

from uuid import uuid4

import pendulum

from app.currency import to_pounds
from harness.providers.base import BaseImportDataProvider


def _get_card_type(slug: str) -> str:
    providers = {
        "amex": "AMEX",
        "visa": "VISA",
        "mastercard": "MASTERCARD",
        "bink-payment": "Bink-Payment",
    }
    return providers[slug]


def rounded_transaction_date(transaction_date):
    dt = pendulum.instance(transaction_date).in_tz("Europe/London")
    rounded = dt.replace(minute=dt.minute + (1 if dt.second >= 30 else 0), second=0)
    return rounded.format("YYYY-MM-DDTHH:mm:ss.SSS")


class WhSmith(BaseImportDataProvider):
    def provide(self, fixture: dict) -> bytes:
        transactions = [
            (
                str(uuid4()),
                "5842003682292310000",
                rounded_transaction_date(transaction["date"]),
                "1579532400",
                fixture["store_id"],
                "Reading",
                "",
                "3",
                str(i * 1000 + j),  # sequence number
                "",
                "682292",
                "",
                "",
                "2",
                to_pounds(transaction["amount"]),
                "",
                "1",
                user["last_four"],
                _get_card_type(fixture["payment_provider"]["slug"]),
                "",
                transaction["auth_code"],
                "***" + transaction["mid"][3:],
                "",
                "GBP",
                "GB",
            )
            for (i, user) in enumerate(fixture["users"], start=1)
            for (j, transaction) in enumerate(user["transactions"])
        ]

        buf = io.StringIO()
        writer = csv.writer(buf, delimiter="|")
        writer.writerows(transactions)
        return buf.getvalue().encode()
