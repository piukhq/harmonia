import string
import typing as t

import pendulum

from app.currency import to_pounds
from harness.providers.base import BaseImportDataProvider

ALPHANUM = string.ascii_letters + string.digits


# field with a fixed length
WidthField = t.Tuple[t.Any, int]


def join(*args: WidthField) -> str:
    return "".join(str(value).ljust(length) for value, length in args)


class MastercardTGX2Settlement(BaseImportDataProvider):
    def provide(self, fixture: dict) -> bytes:
        now = pendulum.now()
        lines = []

        # header
        lines.append(
            join(
                ("H", 1),  # header record
                (now.format("YYYYMMDD"), 8),
                (now.format("hhmmss"), 6),
                ("", 835),  # filler
            )
        )

        # detail
        lines.extend(
            join(
                ("D", 1),
                ("", 20),
                (user["token"], 30),
                ("", 51),
                (pendulum.instance(transaction["date"]).in_tz("Europe/London").format("YYYYMMDD"), 8),
                ("", 341),
                (transaction["identifier"], 15),
                ("", 52),
                (f"{transaction['amount']:012}", 12),
                ("", 33),
                (pendulum.instance(transaction["date"]).in_tz("Europe/London").format("HHmm"), 4),
                (transaction["auth_code"], 6),
                ("", 188),
                (transaction["settlement_key"][:9], 9),  # tx id
            )
            for user in fixture["users"]
            for transaction in user["transactions"]
        )

        # trailer
        lines.append(
            join(
                ("T", 1),  # header record
                (now.format("YYYYMMDD"), 8),
                (now.format("hhmmss"), 6),
                ("", 835),  # filler
            )
        )

        return "\n".join(lines).encode()


class MastercardAuth(BaseImportDataProvider):
    def provide(self, fixture: dict) -> t.List[dict]:
        return [
            {
                "third_party_id": transaction["settlement_key"][:9],
                "time": pendulum.instance(transaction["date"]).in_tz("Europe/London").format("YYYY-MM-DD HH:mm:ss"),
                "amount": str(to_pounds(transaction["amount"])),
                "currency_code": "GBP",
                "payment_card_token": user["token"],
                "mid": transaction["identifier"],
            }
            for user in fixture["users"]
            for transaction in user["transactions"]
        ]
