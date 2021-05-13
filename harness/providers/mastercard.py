import typing as t
import string
from random import randint

import pendulum

from harness.providers.base import BaseImportDataProvider
from app.currency import to_pounds

ALPHANUM = string.ascii_letters + string.digits


# field with a fixed length
WidthField = t.Tuple[t.Any, int]


def join(*args: WidthField) -> str:
    return "".join(str(value).ljust(length) for value, length in args)


class MastercardTS44Settlement(BaseImportDataProvider):
    def provide(self, fixture: dict) -> bytes:
        now = pendulum.now()
        lines = []

        # header
        lines.append(
            join(
                ("H", 1),  # header record
                (now.format("YYYYMMDD"), 8),
                (now.format("hhmmss"), 6),
                ("00000017597", 11),  # member ICA
                ("", 174),  # filler
            )
        )

        lines.extend(
            join(
                ("D", 1),  # data record
                (str(randint(0, 10 ** 12)).rjust(13, "0"), 13),  # tx sequence number
                ("", 19),  # bank account number
                (str(to_pounds(transaction["amount"])).rjust(13, "0"), 13),
                (pendulum.instance(transaction["date"]).format("YYYYMMDD"), 8),
                (fixture["loyalty_scheme"]["slug"].upper(), 60),
                (transaction["mid"], 22),
                (str(randint(0, 10 ** 8)).rjust(9, "0"), 9),  # location ID
                (str(randint(0, 10 ** 5)).rjust(6, "0"), 6),  # issuer ICA code
                (pendulum.instance(transaction["date"]).format("HHmm"), 4),  # transaction time
                (transaction["settlement_key"][:9], 9),  # banknet ref number
                (user["token"], 30),  # bank customer number
                (str(randint(0, 10 ** 5)).rjust(6, "0"), 6),  # aggregate merchant ID
            )
            for user in fixture["users"]
            for transaction in user["transactions"]
        )

        # trailer
        lines.append(
            join(
                ("T", 1),  # trailer record
                (str(len(lines) - 1).rjust(12, "0"), 12),  # record count
                ("00000017597", 11),  # member ICA
                ("", 176),  # filler
            )
        )

        return "\n".join(lines).encode()


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
                (pendulum.instance(transaction["date"]).format("YYYYMMDD"), 8),
                ("", 341),
                (transaction["mid"], 15),
                ("", 52),
                (str(to_pounds(transaction["amount"])).rjust(12, "0"), 12),
                ("", 33),
                (pendulum.instance(transaction["date"]).format("HHmm"), 4),
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
                "mid": transaction["mid"],
            }
            for user in fixture["users"]
            for transaction in user["transactions"]
        ]
