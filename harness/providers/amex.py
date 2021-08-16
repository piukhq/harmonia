import typing as t
from uuid import uuid4

import pendulum

from app.currency import to_pounds
from harness.providers.base import BaseImportDataProvider


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
            pipe(
                "D",  # detail identifier
                "AADP0050",  # partner id
                str(uuid4()),  # transaction ID
                pendulum.instance(transaction["date"]).in_tz("Europe/London").format("YYYY-MM-DD"),
                str(transaction["amount"] / 100).rjust(17, "0"),
                user["token"].ljust(200),
                transaction["mid"].ljust(15),
                pendulum.instance(transaction["date"]).in_tz("Europe/London").format("YYYY-MM-DD-HH.mm.ss"),
                f'{user["first_six"]}XXXXX{user["last_four"]}',
            )
            for user in fixture["users"]
            for transaction in user.get("transactions", [])
        )

        # trailer
        lines.append(
            pipe(
                "T",  # trailer identifier
                "03",  # file type (03 = tlog)
                str(len(lines) - 1).rjust(12, "0"),  # record count
                " " * 263,  # filler
            )
        )

        return "\n".join(lines).encode()


class AmexAuth(BaseImportDataProvider):
    def provide(self, fixture: dict) -> t.List[dict]:
        return [
            {
                "transaction_id": transaction["settlement_key"],
                "offer_id": transaction["settlement_key"],
                "transaction_time": pendulum.instance(transaction["date"]).in_tz("MST").format("YYYY-MM-DD HH:mm:ss"),
                "transaction_amount": to_pounds(transaction["amount"]),
                "cm_alias": user["token"],
                "merchant_number": transaction["mid"],
                "approval_code": transaction["auth_code"],
            }
            for user in fixture["users"]
            for transaction in user["transactions"]
        ]


class AmexSettlement(BaseImportDataProvider):
    def provide(self, fixture: dict) -> t.List[dict]:
        return [
            {
                "transactionId": transaction["settlement_key"],
                "offerId": transaction["settlement_key"],
                "transactionDate": (
                    pendulum.instance(transaction["date"]).in_tz("Europe/London").format("YYYY-MM-DD HH:mm:ss")
                ),
                "transactionAmount": to_pounds(transaction["amount"]),
                "cardToken": user["token"],
                "merchantNumber": transaction["mid"],
                "approvalCode": transaction["auth_code"],
                "dpan": f'{user["first_six"]}XXXXX{user["last_four"]}',
                "partnerId": "AADP0050",
                "recordId": "0224133845625011230183160001602891525AADP00400",
                "currencyCode": "840",
            }
            for user in fixture["users"]
            for transaction in user["transactions"]
        ]
