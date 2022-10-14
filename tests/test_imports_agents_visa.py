from decimal import Decimal

import pendulum

from app import db, models
from app.feeds import FeedType
from app.imports.agents.visa import VisaAuth


def create_transaction_record(db_session: db.Session):
    import_transaction, _ = db.get_or_create(
        models.ImportTransaction,
        transaction_id="1234567",
        data={
            "CardId": "8eaa27e5-",
            "ExternalUserId": "token-234",
            "MessageElementsCollection": [
                {"Key": "Transaction.BillingAmount", "Value": "10.99"},
                {"Key": "Transaction.TimeStampYYMMDD", "Value": "2020-06-02T15:46:00+00:00"},
                {"Key": "Transaction.MerchantCardAcceptorId", "Value": "test-mid-234"},
                {"Key": "Transaction.MerchantAcquirerBin", "Value": "3423432"},
                {"Key": "Transaction.TransactionAmount", "Value": "10.99"},
                {"Key": "Transaction.VipTransactionId", "Value": "8eaa27e5-d9ac-489d-9499-002e78cd32c4"},
                {"Key": "Transaction.VisaMerchantName", "Value": "Bink Shop"},
                {"Key": "Transaction.VisaMerchantId", "Value": "test-mid-234"},
                {"Key": "Transaction.VisaStoreName", "Value": "Bink Shop"},
                {"Key": "Transaction.VisaStoreId", "Value": "tEQeBQRnglCdxJJJSjjqQK7JlosEXy6N0f9756leIh8="},
                {"Key": "Transaction.SettlementDate", "Value": ""},
                {"Key": "Transaction.SettlementAmount", "Value": 0},
                {"Key": "Transaction.SettlementCurrencyCodeNumeric", "Value": 0},
                {"Key": "Transaction.SettlementBillingAmount", "Value": 0},
                {"Key": "Transaction.SettlementBillingCurrency", "Value": ""},
                {"Key": "Transaction.SettlementUSDAmount", "Value": 0},
                {"Key": "Transaction.CurrencyCodeNumeric", "Value": "840"},
                {"Key": "Transaction.BillingCurrencyCode", "Value": "840"},
                {"Key": "Transaction.USDAmount", "Value": "10.99"},
                {"Key": "Transaction.MerchantLocalPurchaseDate ", "Value": "2019-12-19"},
                {"Key": "Transaction.MerchantGroup.0.Name", "Value": "TEST_MG"},
                {"Key": "Transaction.MerchantGroup.0.ExternalId", "Value": "MYSTORE"},
                {"Key": "Transaction.MerchantDateTimeGMT ", "Value": "2019-12-19T23:40:00"},
                {"Key": "Transaction.AuthCode", "Value": "6666667"},
                {"Key": "Transaction.PanLastFour", "Value": "2345"},
            ],
            "MessageId": "12345678",
            "MessageName": "AuthMessageTest",
            "UserDefinedFieldsCollection": [{"Key": "TransactionType", "Value": "AUTH"}],
            "UserProfileId": "f292f99d-babf-528a-8d8a-19fa5f14f4",
        },
        defaults=dict(
            feed_type=FeedType.AUTH,
            provider_slug="visa",
            identified=True,
            match_group="98765",
            source="AMQP: visa-auth",
        ),
        session=db_session,
    )
    return import_transaction


def test_find_new_transactions(db_session: db.Session):
    create_transaction_record(db_session)
    provider_transactions = [
        {
            "TransactionCardFirst6": "434567",
            "TransactionCardLast4": "7890",
            "TransactionCardExpiry": "01/80",
            "TransactionCardSchemeId": 2,
            "TransactionCardScheme": "Visa",
            "TransactionStore_Id": "test-mid-234",
            "TransactionTimestamp": pendulum.DateTime(2020, 6, 2, 16, 46, 0, tzinfo=pendulum.timezone("Europe/London")),
            "TransactionAmountValue": 1099,
            "TransactionAmountUnit": "GBP",
            "TransactionCashbackValue": Decimal("0.00"),
            "TransactionCashbackUnit": "GBP",
            "TransactionId": "b0e2ef76-4dcc-44f9-bd59-f82d3e7c9d3c",
            "TransactionAuthCode": "666665",
        },
        {
            "TransactionCardFirst6": "434567",
            "TransactionCardLast4": "7890",
            "TransactionCardExpiry": "01/80",
            "TransactionCardSchemeId": 2,
            "TransactionCardScheme": "Visa",
            "TransactionStore_Id": "test-mid-234",
            "TransactionTimestamp": pendulum.DateTime(2020, 6, 2, 18, 46, 0, tzinfo=pendulum.timezone("Europe/London")),
            "TransactionAmountValue": 1099,
            "TransactionAmountUnit": "GBP",
            "TransactionCashbackValue": Decimal("0.00"),
            "TransactionCashbackUnit": "GBP",
            "TransactionId": "09cd8488-243a-44a4-a12f-a4cdaa43b4f4",
            "TransactionAuthCode": "666666",
        },
    ]

    agent = VisaAuth()
    agent._find_new_transactions(provider_transactions, db_session)
    pass
