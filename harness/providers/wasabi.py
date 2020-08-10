import csv
import io
import typing as t
from random import randint

import pendulum
from app.currency import to_pounds
from app.imports.agents.wasabi import DATE_FORMAT as IMPORT_DATE_FORMAT
from app.imports.agents.wasabi import TIME_FORMAT as IMPORT_TIME_FORMAT
from harness.providers.base import BaseImportDataProvider


def _get_card_scheme(slug: str) -> t.Tuple[int, str]:
    return {
        "amex": (1, "American Express"),
        "visa": (2, "Visa"),
        "mastercard": (3, "Mastercard"),
        "bink-payment": (9, "Bink-Payment"),
    }[slug]


class Wasabi(BaseImportDataProvider):
    def provide(self, fixture: dict) -> bytes:
        scheme_id, scheme_name = _get_card_scheme(fixture["payment_provider"]["slug"])
        transactions = [
            (
                "A076",
                "16277",
                "123456789",
                "3",
                to_pounds(transaction["amount"]),
                f"{user['first_six']}******{user['last_four']}",
                scheme_name,
                transaction["auth_code"],
                "1",
                pendulum.instance(transaction["date"]).in_tz("Europe/London").format(IMPORT_DATE_FORMAT),
                pendulum.instance(transaction["date"]).in_tz("Europe/London").format(IMPORT_TIME_FORMAT),
                fixture["mid"],
                f"0000A0{str(randint(0, 10 ** 12)).rjust(13, '0')}",
            )
            for user in fixture["users"]
            for transaction in user["transactions"]
        ]

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            (
                "Store No_",
                "Entry No_",
                "Transaction No_",
                "Tender Type",
                "Amount",
                "Card Number",
                "Card Type Name",
                "Auth_code",
                "Authorisation Ok",
                "Date",
                "Time",
                "EFT Merchant No_",
                "Receipt No_",
            )
        )
        writer.writerows(transactions)
        return buf.getvalue().encode()
