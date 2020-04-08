from datetime import datetime
import typing as t
from random import randint

import gnupg
import pendulum

from harness.providers.base import BaseImportDataProvider
import settings
from uuid import uuid4

# field with a fixed length
WidthField = t.Tuple[t.Any, int]


def join(*args: WidthField) -> str:
    return "".join(str(value).ljust(length) for value, length in args)


def format_date(date: datetime) -> str:
    return pendulum.instance(date).format("YYYYMMDD")


def format_time(date: datetime) -> str:
    return pendulum.instance(date).format("hhmm")


def get_transaction_id() -> str:
    return str(uuid4())


class Visa(BaseImportDataProvider):
    def provide(self, fixture: dict) -> bytes:
        gpg = gnupg.GPG(**settings.GPG_ARGS)
        lines = []
        now = pendulum.now().format("YYYYMMDD")

        # header
        lines.append(
            join(
                ("00", 2),  # record type
                ("00", 2),  # record subtype
                ("TAQC", 6),  # sender/source ID
                ("LOYANG", 6),  # receiver/destination ID
                ("Standard Transaction Extract", 255),  # file description
                (now, 8),  # file creation date
                ("", 2),  # file control number
                ("2.0", 4),  # file format version
                ("P", 1),  # test file indicator
                (now, 8),  # content start date
                (now, 8),  # content end date
                ("", 670),  # filler
            )
        )

        # data
        lines.extend(
            (
                join(
                    ("16", 2),  # record type
                    ("01", 2),  # record subtype
                    ("3G", 2),  # promotion type
                    ("B16LOYANPVLOYANGSAUG16AVD", 25),  # promotion code
                    ("05", 2),  # transaction code
                    (str(transaction["amount"]).rjust(15), 15),
                    ("", 21),  # filler
                    ("LOYANG", 6),  # project sponsor ID
                    ("LOYANG", 6),  # promotion group ID
                    ("5411".rjust(34), 34),  # unknown
                    (fixture["loyalty_scheme"]["slug"].upper(), 25),
                    ("ASCOT", 13),  # merchant city
                    ("--", 2),  # merchant state
                    ("00000", 9),  # merchant zip
                    (" 826", 4),  # merchant country
                    (format_date(transaction["date"]), 8),
                    ("", 18),  # filler
                    (fixture["mid"], 15),
                    (format_date(transaction["date"]), 8),
                    (format_time(transaction["date"]), 4),
                    ("", 16),  # filler
                    (format_date(transaction["date"]), 8),
                    (str(randint(0, 10 ** 13)).rjust(14, "0"), 14),  # transaction sequence ID
                    ("", 108),  # filler
                    ("GBP", 3),  # country currency code
                    (str(transaction["amount"]).rjust(15), 15),
                    ("GBP", 3),  # acquirer currency code
                    ("", 44),  # filler
                    (str(randint(0, 10 ** 14)).rjust(15, "0"), 15),  # transaction ID
                    ("", 22),  # filler
                    (str(randint(0, 10 ** 5)).rjust(6, "0"), 6),  # auth code
                    ("", 89),  # filler
                    (user["token"], 25),
                    (format_time(transaction["date"]), 4),
                    ("", 407),  # filler
                )
                for user in fixture["users"]
                for transaction in user["transactions"]
            )
        )

        # trailer
        lines.append(
            join(
                ("99", 2),  # record type
                ("99", 2),  # record subtype
                ("", 10),  # filler
                (str(len(lines) - 1).rjust(10), 10),  # record count
                ("", 10),  # filler
                ("", 966),  # filler
            )
        )

        data = "\n".join(lines)
        enc = gpg.encrypt(data, "harmonia@bink.dev", armor=False)
        return enc.data


class VisaAuth(BaseImportDataProvider):
    def provide(self, fixture: dict) -> t.List[dict]:
        return [
            {
                "cardId": transaction["settlement_key"][:9],
                "externalUserId": user["token"],
                "messageElementsCollection": {
                    "messageElement": [
                        {"key": "User.PromoCode", "value": "10012002"},
                        {"key": "Transaction.VipTransactionId", "value": get_transaction_id()},
                        {
                            "key": "Transaction.TimeStampYYMMDD",
                            "value": pendulum.instance(transaction["date"]).format("YYYY-MM-DDThh:mm:ss"),
                        },
                        {"key": "Transaction.TransactionAmount", "value": transaction["amount"] / 100},
                        {"key": "Transaction.CurrencyCodeNumeric", "value": "840"},
                        {"key": "Transaction.BillingAmount", "value": transaction["amount"] / 100},
                        {"key": "Transaction.BillingCurrencyCode", "value": "840"},
                        {"key": "Transaction.USDAmount", "value": transaction["amount"] / 100},
                        {"key": "Transaction.MerchantCardAcceptorId", "value": "32423 ABC"},
                        {"key": "Transaction.MerchantAcquirerBin", "value": "3423432"},
                        {"key": "Transaction.VisaMerchantId", "value": fixture["mid"]},
                        {"key": "Transaction.VisaMerchantName", "value": "Bink Shop"},
                        {"key": "Transaction.VisaStoreId", "value": fixture["mid"]},
                        {"key": "Transaction.VisaStoreName", "value": "Bink Shop"},
                    ]
                },
                "messageId": "12345678",
                "messageName": "AuthMessageTest",
                "userDefinedFieldsCollection": {"userDefinedField": [{"key": "RandomPropertyName", "value": "value"}]},
                "userProfileId": "f292f99d-babf-528a-8d8a-19fa5f14f4",
            }
            for user in fixture["users"]
            for transaction in user["transactions"]
        ]
