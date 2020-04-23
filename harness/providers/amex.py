import typing as t
from uuid import uuid4

import pendulum

from harness.providers.base import BaseImportDataProvider
from app.currency import to_pounds


def pipe(*args):
    return "|".join(args)


def get_transaction_id() -> str:
    return str(uuid4())


class Amex(BaseImportDataProvider):
    def provide(self, fixture: dict) -> bytes:
        lines = []
        # header
        lines.append(
            pipe(
                "H",  # header identifier
                pendulum.now().format("YYYY-MM-DD"),
                "0000000001",  # sequence number
                "A2P",  # from/to
                "03",  # file type (03 = tlog)
                "AMEX TLOG FILE".ljust(40),  # file description
                " " * 209,  # filler
            )
        )

        lines.extend(
            (
                self._build_transaction(transaction, fixture, user["token"])
                for user in fixture["users"]
                for transaction in user.get("transactions", [])
            )
        )

        lines.extend(
            (
                self._build_transaction(transaction, fixture, transaction["token"])
                for transaction in fixture["loyalty_scheme"].get("transactions", [])
            )
        )

        # trailer
        lines.append(
            pipe(
                "T",  # trialer identifier
                "03",  # file type (03 = tlog)
                str(len(lines) - 1).rjust(12, "0"),  # record count
                " " * 263,  # filler
            )
        )

        return "\n".join(lines).encode()

    @staticmethod
    def _build_transaction(transaction: dict, fixture: dict, token: str) -> dict:
        return pipe(
            "D",  # detail identifier
            "AADP0050",  # partner id
            str(uuid4()),  # transaction ID
            pendulum.instance(transaction["date"]).format("YYYY-MM-DD"),
            str(transaction["amount"] / 100).rjust(17, "0"),
            token.ljust(200),
            fixture["mid"].ljust(15),
            pendulum.instance(transaction["date"]).format("YYYY-MM-DD-hh.mm.ss"),
            f'{transaction["first_six"]}XXXXX{transaction["last_four"]}',
        )


class AmexAuth(BaseImportDataProvider):
    def provide(self, fixture: dict) -> t.List[dict]:
        transactions = [
            self._build_transaction(transaction, fixture, user["token"])
            for user in fixture["users"]
            for transaction in user["transactions"]
        ]

        transactions.extend(
            [
                self._build_transaction(transaction, fixture, transaction["token"])
                for transaction in fixture["loyalty_scheme"].get("transactions", [])
            ]
        )
        return transactions

    @staticmethod
    def _build_transaction(transaction: dict, fixture: dict, token: str) -> dict:
        return {
            "transaction_id": get_transaction_id(),
            "offer_id": transaction["settlement_key"],
            "transaction_time": pendulum.instance(transaction["date"]).format("YYYY-MM-DD hh:mm:ss"),
            "transaction_amount": to_pounds(transaction["amount"]),
            "cm_alias": token,
            "merchant_number": fixture["mid"],
        }
