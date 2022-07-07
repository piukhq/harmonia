import typing as t
from uuid import uuid4

import pendulum

from app.currency import to_pounds
from harness.providers.base import BaseImportDataProvider


def pipe(*args):
    return "|".join(args)


def get_transaction_id() -> str:
    return str(uuid4())


class AmexAuth(BaseImportDataProvider):
    def provide(self, fixture: dict) -> t.List[dict]:
        return [
            {
                "transaction_id": transaction["settlement_key"],
                "offer_id": transaction["settlement_key"],
                "transaction_time": pendulum.instance(transaction["date"]).in_tz("MST").format("YYYY-MM-DD HH:mm:ss"),
                "transaction_amount": to_pounds(transaction["amount"]),
                "cm_alias": user["token"],
                "merchant_number": transaction["identifier"],
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
                "merchantNumber": transaction["identifier"],
                "approvalCode": transaction["auth_code"],
                "dpan": f'{user["first_six"]}XXXXX{user["last_four"]}',
                "partnerId": "AADP0050",
                "recordId": "0224133845625011230183160001602891525AADP00400",
                "currencyCode": "840",
            }
            for user in fixture["users"]
            for transaction in user["transactions"]
        ]
