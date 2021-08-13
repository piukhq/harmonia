import json
import typing as t
from uuid import uuid4

import pendulum

from app.currency import to_pounds
from harness.providers.base import BaseImportDataProvider


def _get_card_scheme(slug: str) -> t.Tuple[int, str]:
    return {
        "amex": (1, "AMERICAN EXPRESS"),
        "visa": (2, "VISA"),
        "mastercard": (3, "MASTERCARD"),
        "bink-payment": (9, "Bink-Payment"),
    }[slug]


class HarveyNichols(BaseImportDataProvider):
    def provide(self, fixture: dict) -> bytes:
        scheme_id, scheme_name = _get_card_scheme(fixture["payment_provider"]["slug"])
        return json.dumps(
            {
                "transactions": [
                    {
                        "alt_id": "",
                        "card": {
                            "first_6": user["first_six"],
                            "last_4": user["last_four"],
                            "expiry": "0",
                            "scheme": scheme_name,
                        },
                        "amount": {"value": float(to_pounds(transaction["amount"])), "unit": "GBP"},
                        "store_id": transaction["store_id"],
                        "timestamp": pendulum.instance(transaction["date"]).in_tz("Europe/London").isoformat(),
                        "id": str(uuid4()),
                        "auth_code": f'00{transaction["auth_code"]}',
                    }
                    for user in fixture["users"]
                    for transaction in user["transactions"]
                ]
            }
        ).encode()
