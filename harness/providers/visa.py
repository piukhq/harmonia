import typing as t
from datetime import datetime

import pendulum

from harness.providers.base import BaseImportDataProvider
from app.currency import to_pounds

# field with a fixed length
WidthField = t.Tuple[t.Any, int]


def join(*args: WidthField) -> str:
    return "".join(str(value).ljust(length) for value, length in args)


def format_date(date: datetime) -> str:
    return pendulum.instance(date).format("YYYYMMDD")


def format_time(date: datetime) -> str:
    return pendulum.instance(date).format("hhmm")


class VisaAuth(BaseImportDataProvider):
    def provide(self, fixture: dict) -> t.List[dict]:
        return [
            {
                "CardId": transaction["settlement_key"][:9],
                "ExternalUserId": user["token"],
                "MessageElementsCollection": [
                    {"Key": "Transaction.BillingAmount", "Value": str(to_pounds(transaction["amount"]))},
                    {"Key": "Transaction.TimeStampYYMMDD", "Value": pendulum.instance(transaction["date"]).isoformat()},
                    {"Key": "Transaction.MerchantCardAcceptorId", "Value": transaction["mid"]},
                    {"Key": "Transaction.MerchantAcquirerBin", "Value": "3423432"},
                    {"Key": "Transaction.TransactionAmount", "Value": str(to_pounds(transaction["amount"]))},
                    {"Key": "Transaction.VipTransactionId", "Value": transaction["settlement_key"]},
                    {"Key": "Transaction.VisaMerchantName", "Value": "Bink Shop"},
                    {"Key": "Transaction.VisaMerchantId", "Value": transaction["mid"]},
                    {"Key": "Transaction.VisaStoreName", "Value": "Bink Shop"},
                    {"Key": "Transaction.VisaStoreId", "Value": transaction["mid"]},
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
                    {"Key": "Transaction.AuthCode", "Value": transaction["auth_code"]},
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
                    {"Key": "Transaction.MerchantCardAcceptorId", "Value": transaction["mid"]},
                    {"Key": "Transaction.MerchantAcquirerBin", "Value": "3423432"},
                    {"Key": "Transaction.TransactionAmount", "Value": str(to_pounds(transaction["amount"]))},
                    {"Key": "Transaction.VipTransactionId", "Value": transaction["settlement_key"]},
                    {"Key": "Transaction.VisaMerchantName", "Value": "Bink Shop"},
                    {"Key": "Transaction.VisaMerchantId", "Value": transaction["mid"]},
                    {"Key": "Transaction.VisaStoreName", "Value": "Bink Shop"},
                    {"Key": "Transaction.VisaStoreId", "Value": transaction["mid"]},
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
                    {"Key": "Transaction.AuthCode", "Value": transaction["auth_code"]},
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
