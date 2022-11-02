import typing as t
from base64 import b64encode
from datetime import datetime
from hashlib import sha256

import pendulum

from app.currency import to_pounds
from harness.providers.base import BaseImportDataProvider

# field with a fixed length
WidthField = t.Tuple[t.Any, int]


def join(*args: WidthField) -> str:
    return "".join(str(value).ljust(length) for value, length in args)


def format_date(date: datetime) -> str:
    return pendulum.instance(date).format("YYYYMMDD")


def format_time(date: datetime) -> str:
    return pendulum.instance(date).format("hhmm")


def vsid(mid: str) -> str:
    return b64encode(sha256(mid.encode()).digest()).decode()


class VisaAuth(BaseImportDataProvider):
    def provide(self, fixture: dict) -> t.List[dict]:
        return [
            {
                "CardId": transaction["settlement_key"][:9],
                "ExternalUserId": user["token"],
                "MessageElementsCollection": [
                    {"Key": "Transaction.BillingAmount", "Value": str(to_pounds(transaction["amount"]))},
                    {"Key": "Transaction.TimeStampYYMMDD", "Value": pendulum.instance(transaction["date"]).isoformat()},
                    {"Key": "Transaction.MerchantCardAcceptorId", "Value": transaction["identifier"]},
                    {"Key": "Transaction.MerchantAcquirerBin", "Value": "3423432"},
                    {"Key": "Transaction.TransactionAmount", "Value": str(to_pounds(transaction["amount"]))},
                    {"Key": "Transaction.VipTransactionId", "Value": transaction["settlement_key"]},
                    {"Key": "Transaction.VisaMerchantName", "Value": "Bink Shop"},
                    {"Key": "Transaction.VisaMerchantId", "Value": transaction["identifier"]},
                    {"Key": "Transaction.VisaStoreName", "Value": "Bink Shop"},
                    {"Key": "Transaction.VisaStoreId", "Value": vsid(transaction["identifier"])},
                    {"Key": "Transaction.SettlementDate", "Value": ""},
                    {"Key": "Transaction.SettlementAmount", "Value": 0},
                    {"Key": "Transaction.SettlementCurrencyCodeNumeric", "Value": 0},
                    {"Key": "Transaction.SettlementBillingAmount", "Value": 0},
                    {"Key": "Transaction.SettlementBillingCurrency", "Value": ""},
                    {"Key": "Transaction.SettlementUSDAmount", "Value": 0},
                    {"Key": "Transaction.CurrencyCodeNumeric", "Value": "840"},
                    {"Key": "Transaction.BillingCurrencyCode", "Value": "840"},
                    {"Key": "Transaction.USDAmount", "Value": str(to_pounds(transaction["amount"]))},
                    {"Key": "Transaction.MerchantLocalPurchaseDate ", "Value": "2019-12-19"},
                    {"Key": "Transaction.MerchantGroup.0.Name", "Value": "TEST_MG"},
                    {"Key": "Transaction.MerchantGroup.0.ExternalId", "Value": "MYSTORE"},
                    {"Key": "Transaction.MerchantDateTimeGMT ", "Value": "2019-12-19T23:40:00"},
                    {"Key": "Transaction.AuthCode", "Value": transaction.get("auth_code", "")},
                    {"Key": "Transaction.PanLastFour", "Value": "2345"},
                ],
                "MessageId": "12345678",
                "MessageName": "AuthMessageTest",
                "UserDefinedFieldsCollection": [{"Key": "TransactionType", "Value": "AUTH"}],
                "UserProfileId": "f292f99d-babf-528a-8d8a-19fa5f14f4",
            }
            for user in fixture["users"]
            for transaction in user["transactions"]
        ]


class VisaSettlement(BaseImportDataProvider):
    def provide(self, fixture: dict) -> t.List[dict]:
        return [
            {
                "CardId": transaction["settlement_key"][:9],
                "ExternalUserId": user["token"],
                "MessageElementsCollection": [
                    {"Key": "Transaction.BillingAmount", "Value": str(to_pounds(transaction["amount"]))},
                    {"Key": "Transaction.TimeStampYYMMDD", "Value": pendulum.instance(transaction["date"]).isoformat()},
                    {"Key": "Transaction.MerchantCardAcceptorId", "Value": transaction["identifier"]},
                    {"Key": "Transaction.MerchantAcquirerBin", "Value": "3423432"},
                    {"Key": "Transaction.TransactionAmount", "Value": str(to_pounds(transaction["amount"]))},
                    {"Key": "Transaction.VipTransactionId", "Value": transaction["settlement_key"]},
                    {"Key": "Transaction.VisaMerchantName", "Value": "Bink Shop"},
                    {"Key": "Transaction.VisaMerchantId", "Value": transaction["identifier"]},
                    {"Key": "Transaction.VisaStoreName", "Value": "Bink Shop"},
                    {"Key": "Transaction.VisaStoreId", "Value": vsid(transaction["identifier"])},
                    {"Key": "Transaction.SettlementDate", "Value": pendulum.now().isoformat()},
                    {"Key": "Transaction.SettlementAmount", "Value": str(to_pounds(transaction["amount"]))},
                    {"Key": "Transaction.SettlementCurrencyCodeNumeric", "Value": 826},
                    {"Key": "Transaction.SettlementBillingAmount", "Value": str(to_pounds(transaction["amount"]))},
                    {"Key": "Transaction.SettlementBillingCurrency", "Value": "GBP"},
                    {"Key": "Transaction.SettlementUSDAmount", "Value": str(to_pounds(transaction["amount"]))},
                    {"Key": "Transaction.CurrencyCodeNumeric", "Value": "840"},
                    {"Key": "Transaction.BillingCurrencyCode", "Value": "840"},
                    {"Key": "Transaction.USDAmount", "Value": str(to_pounds(transaction["amount"]))},
                    {"Key": "Transaction.MerchantLocalPurchaseDate", "Value": "2019-12-19"},
                    {"Key": "Transaction.MerchantGroup.0.Name", "Value": "TEST_MG"},
                    {"Key": "Transaction.MerchantGroup.0.ExternalId", "Value": "MYSTORE"},
                    {
                        "Key": "Transaction.MerchantDateTimeGMT",
                        "Value": pendulum.instance(transaction["date"]).isoformat(),
                    },
                    {"Key": "Transaction.AuthCode", "Value": transaction.get("auth_code", "")},
                    {"Key": "Transaction.PanLastFour", "Value": "2345"},
                ],
                "MessageId": "12345678",
                "MessageName": "SettlementMessageTest",
                "UserDefinedFieldsCollection": [{"Key": "TransactionType", "Value": "SETTLE"}],
                "UserProfileId": "f292f99d-babf-528a-8d8a-19fa5f14f4",
            }
            for user in fixture["users"]
            for transaction in user["transactions"]
        ]


class VisaRefund(BaseImportDataProvider):
    def provide(self, fixture: dict) -> t.List[dict]:
        return [
            {
                "CardId": transaction["settlement_key"][:9],
                "ExternalUserId": user["token"],
                "MessageElementsCollection": [
                    {
                        "Key": "ReturnTransaction.DateTime",
                        "Value": pendulum.instance(transaction["date"]).format("M/D/YYYY h:m:s A"),
                    },
                    {"Key": "ReturnTransaction.CardAcceptorIdCode", "Value": transaction["identifier"]},
                    {"Key": "ReturnTransaction.AcquirerBIN", "Value": "3423432"},
                    {"Key": "ReturnTransaction.Amount", "Value": str(to_pounds(transaction["amount"]))},
                    {"Key": "ReturnTransaction.VipTransactionId", "Value": transaction["settlement_key"]},
                    {"Key": "ReturnTransaction.SettlementId", "Value": transaction["settlement_key"]},
                    {"Key": "ReturnTransaction.VisaMerchantName", "Value": "Bink Shop"},
                    {"Key": "ReturnTransaction.VisaMerchantId", "Value": transaction["identifier"]},
                    {"Key": "ReturnTransaction.VisaStoreName", "Value": "Bink Shop"},
                    {"Key": "ReturnTransaction.VisaStoreId", "Value": vsid(transaction["identifier"])},
                    {"Key": "ReturnTransaction.AcquirerAmount", "Value": str(to_pounds(transaction["amount"]))},
                    {"Key": "ReturnTransaction.AcquirerCurrencyCode", "Value": 826},
                    {"Key": "ReturnTransaction.CurrencyCode", "Value": "840"},
                    {"Key": "ReturnTransaction.TransactionUSDAmount", "Value": str(to_pounds(transaction["amount"]))},
                    {"Key": "ReturnTransaction.MerchantGroupName.0.Name", "Value": "TEST_MG"},
                    {"Key": "ReturnTransaction.MerchantGroupName.0.ExternalId", "Value": "MYSTORE"},
                    {"Key": "ReturnTransaction.AuthCode", "Value": transaction.get("auth_code", "")},
                ],
                "MessageId": "12345678",
                "MessageName": "SettlementMessageTest",
                "UserDefinedFieldsCollection": [{"Key": "TransactionType", "Value": "RETURN"}],
                "UserProfileId": "f292f99d-babf-528a-8d8a-19fa5f14f4",
            }
            for user in fixture["users"]
            for transaction in user["transactions"]
        ]
