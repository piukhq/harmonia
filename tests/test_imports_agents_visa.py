import json

from app import db, models
from app.feeds import FeedType
from app.imports.agents.visa import VisaAuth

transaction_1_id = "MTY1NzkzM0EtNDI1OS00MjA2LUIxNjEtRUE1RTE2NDY3ODM0"
transaction_1 = {
    "CardId": "NTI4QjdBNUEtRDE0QS00Q0YzLTkyOTAtQkI4NkQxNjJDMkU2",
    "ExternalUserId": "test_card_token_1",
    "MessageElementsCollection": [
        {"Key": "Transaction.MerchantCardAcceptorId", "Value": "test_primary_identifier_1"},
        {"Key": "Transaction.MerchantAcquirerBin", "Value": "3423432"},
        {"Key": "Transaction.TransactionAmount", "Value": "96.00"},
        {"Key": "Transaction.VipTransactionId", "Value": transaction_1_id},
        {"Key": "Transaction.VisaMerchantName", "Value": ""},
        {"Key": "Transaction.VisaMerchantId", "Value": ""},
        {"Key": "Transaction.VisaStoreName", "Value": ""},
        {"Key": "Transaction.VisaStoreId", "Value": ""},
        {"Key": "Transaction.CurrencyCodeNumeric", "Value": "840"},
        {"Key": "Transaction.BillingCurrencyCode", "Value": "840"},
        {"Key": "Transaction.USDAmount", "Value": "96.00"},
        {"Key": "Transaction.MerchantLocalPurchaseDate", "Value": "2022-10-14"},
        {"Key": "Transaction.MerchantGroup.0.Name", "Value": "ICELAND-BONUS-CARD"},
        {"Key": "Transaction.MerchantGroup.0.ExternalId", "Value": "Iceland"},
        {"Key": "Transaction.AuthCode", "Value": "822643"},
        {"Key": "Transaction.PanLastFour", "Value": "7890"},
        {"Key": "Transaction.MerchantDateTimeGMT", "Value": "2022-10-14 12:52:24"},
        {"Key": "Transaction.BillingAmount", "Value": "96.00"},
        {"Key": "Transaction.TimeStampYYMMDD", "Value": "2022-10-14 12:52:24"},
        {"Key": "Transaction.SettlementDate", "Value": ""},
        {"Key": "Transaction.SettlementAmount", "Value": "0"},
        {"Key": "Transaction.SettlementCurrencyCodeNumeric", "Value": "0"},
        {"Key": "Transaction.SettlementBillingAmount", "Value": "0"},
        {"Key": "Transaction.SettlementBillingCurrency", "Value": ""},
        {"Key": "Transaction.SettlementUSDAmount", "Value": "0"},
    ],
    "MessageId": "B0997DCE-7025-4E28-B890-09E755575698",
    "MessageName": "AuthMessageTest",
    "UserDefinedFieldsCollection": [{"Key": "TransactionType", "Value": "Auth"}],
    "UserProfileId": "510D7DE9-4C4F-407D-8072-53C747192226",
}
transaction_2 = {
    "CardId": "MkNGQjc3QjktOUFDMy00RTM2LUIwRTMtM0QyMjU0NkY4OEFB",
    "ExternalUserId": "test_token_2",
    "MessageElementsCollection": [
        {"Key": "Transaction.MerchantCardAcceptorId", "Value": "test_primary_identifier_2"},
        {"Key": "Transaction.MerchantAcquirerBin", "Value": "3423432"},
        {"Key": "Transaction.TransactionAmount", "Value": "41.00"},
        {"Key": "Transaction.VipTransactionId", "Value": "RDRGOEFEMkYtQkJFMC00MzhGLTk5MDktQjVCOEQ0M0VBM0ZD"},
        {"Key": "Transaction.VisaMerchantName", "Value": ""},
        {"Key": "Transaction.VisaMerchantId", "Value": ""},
        {"Key": "Transaction.VisaStoreName", "Value": ""},
        {"Key": "Transaction.VisaStoreId", "Value": ""},
        {"Key": "Transaction.CurrencyCodeNumeric", "Value": "840"},
        {"Key": "Transaction.BillingCurrencyCode", "Value": "840"},
        {"Key": "Transaction.USDAmount", "Value": "41.00"},
        {"Key": "Transaction.MerchantLocalPurchaseDate", "Value": "2022-10-14"},
        {"Key": "Transaction.MerchantGroup.0.Name", "Value": "ICELAND-BONUS-CARD"},
        {"Key": "Transaction.MerchantGroup.0.ExternalId", "Value": "Iceland"},
        {"Key": "Transaction.AuthCode", "Value": "745615"},
        {"Key": "Transaction.PanLastFour", "Value": "8901"},
        {"Key": "Transaction.MerchantDateTimeGMT", "Value": "2022-10-14 12:54:59"},
        {"Key": "Transaction.BillingAmount", "Value": "41.00"},
        {"Key": "Transaction.TimeStampYYMMDD", "Value": "2022-10-14 12:54:59"},
        {"Key": "Transaction.SettlementDate", "Value": ""},
        {"Key": "Transaction.SettlementAmount", "Value": "0"},
        {"Key": "Transaction.SettlementCurrencyCodeNumeric", "Value": "0"},
        {"Key": "Transaction.SettlementBillingAmount", "Value": "0"},
        {"Key": "Transaction.SettlementBillingCurrency", "Value": ""},
        {"Key": "Transaction.SettlementUSDAmount", "Value": "0"},
    ],
    "MessageId": "9F4707B5-7787-40AF-8976-C7B6DBC5AF68",
    "MessageName": "AuthMessageTest",
    "UserDefinedFieldsCollection": [{"Key": "TransactionType", "Value": "Auth"}],
    "UserProfileId": "88BD801E-8A2C-4952-A448-CAA5D1E9BDCD",
}


def create_transaction_record(db_session: db.Session):
    db.get_or_create(
        models.ImportTransaction,
        transaction_id=transaction_1_id,
        defaults=dict(
            feed_type=FeedType.AUTH,
            provider_slug="visa",
            identified=True,
            match_group="e5ccfe848bd94825b921b677d3baf1b1",
            source="AMQP: visa-auth",
            data=json.dumps(transaction_1),
        ),
        session=db_session,
    )


def test_find_new_transactions(db_session: db.Session):
    create_transaction_record(db_session)
    provider_transactions = [transaction_1, transaction_2]

    agent = VisaAuth()
    new_transactions = agent._find_new_transactions(provider_transactions, session=db_session)

    assert new_transactions[0] == transaction_2
