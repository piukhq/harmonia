import copy

from app.imports.agents.visa import VisaAuth, get_valid_identifiers
from app.models import IdentifierType

tx_data = {
    "CardId": "744e4f00-",
    "ExternalUserId": "token-123",
    "MessageElementsCollection": [
        {"Key": "Transaction.BillingAmount", "Value": "89.45"},
        {"Key": "Transaction.TimeStampYYMMDD", "Value": "2020-10-27T15:01:59+00:00"},
        {"Key": "Transaction.MerchantCardAcceptorId", "Value": "test-mid-123"},
        {"Key": "Transaction.MerchantAcquirerBin", "Value": "3423432"},
        {"Key": "Transaction.TransactionAmount", "Value": "89.45"},
        {"Key": "Transaction.VipTransactionId", "Value": "744e4f00-26af-448f-add8-a8c8486c0248"},
        {"Key": "Transaction.VisaMerchantName", "Value": "Bink Shop"},
        {"Key": "Transaction.VisaMerchantId", "Value": "test-mid-456"},
        {"Key": "Transaction.VisaStoreName", "Value": "Bink Shop"},
        {"Key": "Transaction.VisaStoreId", "Value": "N+4j+mjB3TDKdu3jO0F3SXQhI2kOITLgxs9isjyo8Ss="},
        {"Key": "Transaction.SettlementDate", "Value": ""},
        {"Key": "Transaction.SettlementAmount", "Value": 0},
        {"Key": "Transaction.SettlementCurrencyCodeNumeric", "Value": 0},
        {"Key": "Transaction.SettlementBillingAmount", "Value": 0},
        {"Key": "Transaction.SettlementBillingCurrency", "Value": ""},
        {"Key": "Transaction.SettlementUSDAmount", "Value": 0},
        {"Key": "Transaction.CurrencyCodeNumeric", "Value": "840"},
        {"Key": "Transaction.BillingCurrencyCode", "Value": "840"},
        {"Key": "Transaction.USDAmount", "Value": "89.45"},
        {"Key": "Transaction.MerchantLocalPurchaseDate ", "Value": "2019-12-19"},
        {"Key": "Transaction.MerchantGroup.0.Name", "Value": "TEST_MG"},
        {"Key": "Transaction.MerchantGroup.0.ExternalId", "Value": "MYSTORE"},
        {"Key": "Transaction.MerchantDateTimeGMT ", "Value": "2019-12-19T23:40:00"},
        {"Key": "Transaction.AuthCode", "Value": "444444"},
        {"Key": "Transaction.PanLastFour", "Value": "2345"},
    ],
    "MessageId": "12345678",
    "MessageName": "AuthMessageTest",
    "UserDefinedFieldsCollection": [{"Key": "TransactionType", "Value": "AUTH"}],
    "UserProfileId": "f292f99d-babf-528a-8d8a-19fa5f14f4",
}


def test_get_valid_identifiers():
    identifier_mapping = {
        IdentifierType.PRIMARY: "Transaction.MerchantCardAcceptorId",
        IdentifierType.SECONDARY: "Transaction.VisaStoreId",
        IdentifierType.PSIMI: "Transaction.VisaMerchantId",
    }
    ids = get_valid_identifiers(tx_data, identifier_mapping)
    assert ids == ["test-mid-123", "N+4j+mjB3TDKdu3jO0F3SXQhI2kOITLgxs9isjyo8Ss=", "test-mid-456"]


def test_get_valid_identifiers_empty_string():
    data = copy.deepcopy(tx_data)
    data["MessageElementsCollection"][7] = {"Key": "Transaction.VisaMerchantId", "Value": ""}
    identifier_mapping = {
        IdentifierType.PRIMARY: "Transaction.MerchantCardAcceptorId",
        IdentifierType.SECONDARY: "Transaction.VisaStoreId",
        IdentifierType.PSIMI: "Transaction.VisaMerchantId",
    }
    ids = get_valid_identifiers(data, identifier_mapping)
    assert ids == ["test-mid-123", "N+4j+mjB3TDKdu3jO0F3SXQhI2kOITLgxs9isjyo8Ss="]


def test_get_identifiers_from_data():
    agent = VisaAuth()
    ids = agent.get_identifiers(tx_data)
    assert ids == ["test-mid-123", "N+4j+mjB3TDKdu3jO0F3SXQhI2kOITLgxs9isjyo8Ss=", "test-mid-456"]
