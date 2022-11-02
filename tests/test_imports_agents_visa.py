import copy
import json
from unittest.mock import patch

import pytest

from app import db, models
from app.feeds import FeedType
from app.imports.agents.visa import VisaAuth, VisaRefund, VisaSettlement, validate_mids
from app.models import IdentifierType

transaction_1_id = "MTY1NzkzM0EtNDI1OS00MjA2LUIxNjEtRUE1RTE2NDY3ODM0"
transaction_1_primary_id = "test_primary_identifier_1"
transaction_1_secondary_id = "N+4j+mjB3TDKdu3jO0F3SXQhI2kOITLgxs9isjyo8Ss="
transaction_1_psimi_id = "test-mid-456"

auth_transaction_1 = {
    "CardId": "NTI4QjdBNUEtRDE0QS00Q0YzLTkyOTAtQkI4NkQxNjJDMkU2",
    "ExternalUserId": "test_card_token_1",
    "MessageElementsCollection": [
        {"Key": "Transaction.MerchantCardAcceptorId", "Value": transaction_1_primary_id},
        {"Key": "Transaction.MerchantAcquirerBin", "Value": "3423432"},
        {"Key": "Transaction.TransactionAmount", "Value": "96.00"},
        {"Key": "Transaction.VipTransactionId", "Value": transaction_1_id},
        {"Key": "Transaction.VisaMerchantName", "Value": ""},
        {"Key": "Transaction.VisaMerchantId", "Value": transaction_1_psimi_id},
        {"Key": "Transaction.VisaStoreName", "Value": ""},
        {"Key": "Transaction.VisaStoreId", "Value": transaction_1_secondary_id},
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

auth1_auth_code_index = auth_transaction_1.get("MessageElementsCollection").index(
    {"Key": "Transaction.AuthCode", "Value": "822643"}
)

auth_psimi_index = auth_transaction_1.get("MessageElementsCollection").index(
    {"Key": "Transaction.VisaMerchantId", "Value": transaction_1_psimi_id}
)

auth_transaction_2 = {
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

settlement_transaction = {
    "CardId": "32c26a8d-",
    "ExternalUserId": "token-234",
    "MessageElementsCollection": [
        {"Key": "Transaction.BillingAmount", "Value": "10.99"},
        {"Key": "Transaction.TimeStampYYMMDD", "Value": "2020-06-02T15:46:00+00:00"},
        {"Key": "Transaction.MerchantCardAcceptorId", "Value": transaction_1_primary_id},
        {"Key": "Transaction.MerchantAcquirerBin", "Value": "3423432"},
        {"Key": "Transaction.TransactionAmount", "Value": "10.99"},
        {"Key": "Transaction.VipTransactionId", "Value": "32c26a8d-95be-4923-b78e-e49ac7d8812d"},
        {"Key": "Transaction.VisaMerchantName", "Value": "Bink Shop"},
        {"Key": "Transaction.VisaMerchantId", "Value": transaction_1_psimi_id},
        {"Key": "Transaction.VisaStoreName", "Value": "Bink Shop"},
        {"Key": "Transaction.VisaStoreId", "Value": transaction_1_secondary_id},
        {"Key": "Transaction.SettlementDate", "Value": "2022-08-15T17:28:42.988530+01:00"},
        {"Key": "Transaction.SettlementAmount", "Value": "10.99"},
        {"Key": "Transaction.SettlementCurrencyCodeNumeric", "Value": 826},
        {"Key": "Transaction.SettlementBillingAmount", "Value": "10.99"},
        {"Key": "Transaction.SettlementBillingCurrency", "Value": "GBP"},
        {"Key": "Transaction.SettlementUSDAmount", "Value": "10.99"},
        {"Key": "Transaction.CurrencyCodeNumeric", "Value": "840"},
        {"Key": "Transaction.BillingCurrencyCode", "Value": "840"},
        {"Key": "Transaction.USDAmount", "Value": "10.99"},
        {"Key": "Transaction.MerchantLocalPurchaseDate", "Value": "2019-12-19"},
        {"Key": "Transaction.MerchantGroup.0.Name", "Value": "TEST_MG"},
        {"Key": "Transaction.MerchantGroup.0.ExternalId", "Value": "MYSTORE"},
        {"Key": "Transaction.MerchantDateTimeGMT", "Value": "2020-06-02T15:46:00+00:00"},
        {"Key": "Transaction.AuthCode", "Value": "6666667"},
        {"Key": "Transaction.PanLastFour", "Value": "2345"},
    ],
    "MessageId": "12345678",
    "MessageName": "SettlementMessageTest",
    "UserDefinedFieldsCollection": [{"Key": "TransactionType", "Value": "SETTLE"}],
    "UserProfileId": "f292f99d-babf-528a-8d8a-19fa5f14f4",
}
settlement_psimi_index = settlement_transaction.get("MessageElementsCollection").index(
    {"Key": "Transaction.VisaMerchantId", "Value": transaction_1_psimi_id}
)

settlement_auth_index = settlement_transaction.get("MessageElementsCollection").index(
    {"Key": "Transaction.AuthCode", "Value": "6666667"}
)

refund_transaction = {
    "CardId": "d5e121cf-",
    "ExternalUserId": "token-123",
    "MessageElementsCollection": [
        {"Key": "ReturnTransaction.DateTime", "Value": "10/27/2020 3:1:59 PM"},
        {"Key": "ReturnTransaction.CardAcceptorIdCode", "Value": transaction_1_primary_id},
        {"Key": "ReturnTransaction.AcquirerBIN", "Value": "3423432"},
        {"Key": "ReturnTransaction.Amount", "Value": "89.45"},
        {"Key": "ReturnTransaction.VipTransactionId", "Value": "d5e121cf-f34a-47ac-be19-908fc09db1ad"},
        {"Key": "ReturnTransaction.SettlementId", "Value": "d5e121cf-f34a-47ac-be19-908fc09db1ad"},
        {"Key": "ReturnTransaction.VisaMerchantName", "Value": "Bink Shop"},
        {"Key": "ReturnTransaction.VisaMerchantId", "Value": transaction_1_psimi_id},
        {"Key": "ReturnTransaction.VisaStoreName", "Value": "Bink Shop"},
        {"Key": "ReturnTransaction.VisaStoreId", "Value": transaction_1_secondary_id},
        {"Key": "ReturnTransaction.AcquirerAmount", "Value": "89.45"},
        {"Key": "ReturnTransaction.AcquirerCurrencyCode", "Value": 826},
        {"Key": "ReturnTransaction.CurrencyCode", "Value": "840"},
        {"Key": "ReturnTransaction.TransactionUSDAmount", "Value": "89.45"},
        {"Key": "ReturnTransaction.MerchantGroupName.0.Name", "Value": "TEST_MG"},
        {"Key": "ReturnTransaction.MerchantGroupName.0.ExternalId", "Value": "MYSTORE"},
        {"Key": "ReturnTransaction.AuthCode", "Value": "444444"},
    ],
    "MessageId": "12345678",
    "MessageName": "SettlementMessageTest",
    "UserDefinedFieldsCollection": [{"Key": "TransactionType", "Value": "RETURN"}],
    "UserProfileId": "f292f99d-babf-528a-8d8a-19fa5f14f4",
}
refund_psimi_index = refund_transaction.get("MessageElementsCollection").index(
    {"Key": "ReturnTransaction.VisaMerchantId", "Value": transaction_1_psimi_id}
)

refund_auth_index = refund_transaction.get("MessageElementsCollection").index(
    {"Key": "ReturnTransaction.AuthCode", "Value": "444444"}
)


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
            data=json.dumps(auth_transaction_1),
        ),
        session=db_session,
    )


def test_find_new_transactions(db_session: db.Session):
    create_transaction_record(db_session)
    provider_transactions = [auth_transaction_1, auth_transaction_2]

    agent = VisaAuth()
    new_transactions = agent._find_new_transactions(provider_transactions, session=db_session)

    assert new_transactions[0] == auth_transaction_2


@pytest.mark.parametrize(
    "input, expected",
    [
        (
            [
                (IdentifierType.PRIMARY, transaction_1_primary_id),
                (IdentifierType.SECONDARY, transaction_1_secondary_id),
                (IdentifierType.PSIMI.value, transaction_1_psimi_id),
            ],
            [
                (IdentifierType.PRIMARY, transaction_1_primary_id),
                (IdentifierType.SECONDARY, transaction_1_secondary_id),
                (IdentifierType.PSIMI.value, transaction_1_psimi_id),
            ],
        ),
        (
            [
                (IdentifierType.PRIMARY, transaction_1_primary_id),
                (IdentifierType.SECONDARY, transaction_1_secondary_id),
                (IdentifierType.PSIMI.value, ""),
            ],
            [
                (IdentifierType.PRIMARY, transaction_1_primary_id),
                (IdentifierType.SECONDARY, transaction_1_secondary_id),
            ],
        ),
        (
            [
                (IdentifierType.PRIMARY, transaction_1_primary_id),
                (IdentifierType.SECONDARY, transaction_1_secondary_id),
                (IdentifierType.PSIMI.value, "0"),
            ],
            [
                (IdentifierType.PRIMARY, transaction_1_primary_id),
                (IdentifierType.SECONDARY, transaction_1_secondary_id),
            ],
        ),
        (
            [
                (IdentifierType.PRIMARY, transaction_1_primary_id),
                (IdentifierType.SECONDARY, transaction_1_secondary_id),
                (IdentifierType.PSIMI.value, None),
            ],
            [
                (IdentifierType.PRIMARY, transaction_1_primary_id),
                (IdentifierType.SECONDARY, transaction_1_secondary_id),
            ],
        ),
    ],
)
def test_get_identifiers(input, expected):
    identifiers = input
    ids = validate_mids(identifiers)
    assert ids == expected


def test_auth_get_mids():
    agent = VisaAuth()
    ids = agent.get_mids(auth_transaction_1)
    assert ids == [
        (IdentifierType.PRIMARY, transaction_1_primary_id),
        (IdentifierType.SECONDARY, transaction_1_secondary_id),
        (IdentifierType.PSIMI, transaction_1_psimi_id),
    ]


def test_auth_get_mids_empty_string():
    data = copy.deepcopy(auth_transaction_1)
    data["MessageElementsCollection"][auth_psimi_index] = {"Key": "Transaction.VisaMerchantId", "Value": ""}
    agent = VisaAuth()
    ids = agent.get_mids(data)
    assert ids == [
        (IdentifierType.PRIMARY, transaction_1_primary_id),
        (IdentifierType.SECONDARY, transaction_1_secondary_id),
    ]


def test_auth_get_mids_null_value():
    data = copy.deepcopy(auth_transaction_1)
    data["MessageElementsCollection"][auth_psimi_index] = {"Key": "Transaction.VisaMerchantId", "Value": None}
    agent = VisaAuth()
    ids = agent.get_mids(data)
    assert ids == [
        (IdentifierType.PRIMARY, transaction_1_primary_id),
        (IdentifierType.SECONDARY, transaction_1_secondary_id),
    ]


def test_auth_get_mids_zero_string():
    data = copy.deepcopy(auth_transaction_1)
    data["MessageElementsCollection"][auth_psimi_index] = {"Key": "Transaction.VisaMerchantId", "Value": "0"}
    agent = VisaAuth()
    ids = agent.get_mids(data)
    assert ids == [
        (IdentifierType.PRIMARY, transaction_1_primary_id),
        (IdentifierType.SECONDARY, transaction_1_secondary_id),
    ]


def test_settlement_get_mids():
    agent = VisaSettlement()
    ids = agent.get_mids(settlement_transaction)
    assert ids == [
        (IdentifierType.PRIMARY, transaction_1_primary_id),
        (IdentifierType.SECONDARY, transaction_1_secondary_id),
        (IdentifierType.PSIMI, transaction_1_psimi_id),
    ]


def test_settlement_get_mids_empty_string():
    data = copy.deepcopy(settlement_transaction)
    data["MessageElementsCollection"][settlement_psimi_index] = {"Key": "Transaction.VisaMerchantId", "Value": ""}
    agent = VisaSettlement()
    ids = agent.get_mids(data)
    assert ids == [
        (IdentifierType.PRIMARY, transaction_1_primary_id),
        (IdentifierType.SECONDARY, transaction_1_secondary_id),
    ]


def test_settlement_get_mids_null_value():
    data = copy.deepcopy(settlement_transaction)
    data["MessageElementsCollection"][settlement_psimi_index] = {"Key": "Transaction.VisaMerchantId", "Value": None}
    agent = VisaSettlement()
    ids = agent.get_mids(data)
    assert ids == [
        (IdentifierType.PRIMARY, transaction_1_primary_id),
        (IdentifierType.SECONDARY, transaction_1_secondary_id),
    ]


def test_settlement_get_mids_zero_string():
    data = copy.deepcopy(settlement_transaction)
    data["MessageElementsCollection"][settlement_psimi_index] = {"Key": "Transaction.VisaMerchantId", "Value": "0"}
    agent = VisaSettlement()
    ids = agent.get_mids(data)
    assert ids == [
        (IdentifierType.PRIMARY, transaction_1_primary_id),
        (IdentifierType.SECONDARY, transaction_1_secondary_id),
    ]


def test_refund_get_mids():
    agent = VisaRefund()
    ids = agent.get_mids(refund_transaction)
    assert ids == [
        (IdentifierType.PRIMARY, transaction_1_primary_id),
        (IdentifierType.SECONDARY, transaction_1_secondary_id),
        (IdentifierType.PSIMI, transaction_1_psimi_id),
    ]


def test_refund_get_mids_empty_string():
    data = copy.deepcopy(refund_transaction)
    data["MessageElementsCollection"][refund_psimi_index] = {"Key": "ReturnTransaction.VisaMerchantId", "Value": ""}
    agent = VisaRefund()
    ids = agent.get_mids(data)
    assert ids == [
        (IdentifierType.PRIMARY, transaction_1_primary_id),
        (IdentifierType.SECONDARY, transaction_1_secondary_id),
    ]


def test_refund_get_mids_null_value():
    data = copy.deepcopy(refund_transaction)
    data["MessageElementsCollection"][refund_psimi_index] = {"Key": "ReturnTransaction.VisaMerchantId", "Value": None}
    agent = VisaRefund()
    ids = agent.get_mids(data)
    assert ids == [
        (IdentifierType.PRIMARY, transaction_1_primary_id),
        (IdentifierType.SECONDARY, transaction_1_secondary_id),
    ]


def test_refund_get_mids_zero_string():
    data = copy.deepcopy(refund_transaction)
    data["MessageElementsCollection"][refund_psimi_index] = {"Key": "ReturnTransaction.VisaMerchantId", "Value": "0"}
    agent = VisaRefund()
    ids = agent.get_mids(data)
    assert ids == [
        (IdentifierType.PRIMARY, transaction_1_primary_id),
        (IdentifierType.SECONDARY, transaction_1_secondary_id),
    ]


@patch("app.imports.agents.visa.VisaAuth.get_merchant_slug", return_value="merchant")
def test_auth_auth_code_field_is_missing(mock_get_merchant_slug):
    data = copy.deepcopy(auth_transaction_1)
    data["MessageElementsCollection"][auth1_auth_code_index] = {"Key": "Transaction.AuthCode", "Value": ""}
    agent = VisaAuth()
    fields = agent.to_transaction_fields(data)
    assert fields.auth_code == ""
    data["MessageElementsCollection"].pop(auth1_auth_code_index)
    fields = agent.to_transaction_fields(data)
    assert fields.auth_code == ""


@patch("app.imports.agents.visa.VisaRefund.get_merchant_slug", return_value="merchant")
def test_refund_auth_code_field_is_missing(mock_get_merchant_slug):
    data = copy.deepcopy(refund_transaction)
    data["MessageElementsCollection"][refund_auth_index] = {"Key": "ReturnTransaction.AuthCode", "Value": ""}
    agent = VisaRefund()
    fields = agent.to_transaction_fields(data)
    assert fields.auth_code == ""
    data["MessageElementsCollection"].pop(refund_auth_index)
    fields = agent.to_transaction_fields(data)
    assert fields.auth_code == ""


@patch("app.imports.agents.visa.VisaSettlement.get_merchant_slug", return_value="merchant")
def test_settlement_auth_code_field_is_missing(mock_get_merchant_slug):
    data = copy.deepcopy(settlement_transaction)
    data["MessageElementsCollection"][refund_auth_index] = {"Key": "Transaction.AuthCode", "Value": ""}
    agent = VisaSettlement()
    fields = agent.to_transaction_fields(data)
    assert fields.auth_code == ""
    data["MessageElementsCollection"].pop(settlement_auth_index)
    fields = agent.to_transaction_fields(data)
    assert fields.auth_code == ""
