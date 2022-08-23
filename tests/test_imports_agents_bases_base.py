from unittest import mock

import pytest

from app import db, models
from app.imports.agents.visa import VisaAuth
from app.imports.exceptions import MissingMID
from app.models import IdentifierType, LoyaltyScheme, PaymentProvider

data = ["test-mid-primary", "test-mid-secondary", "test-mid-psimi"]

visa_transaction = {
    "CardId": "f237df3e-",
    "ExternalUserId": "token-123",
    "MessageElementsCollection": [
        {"Key": "Transaction.BillingAmount", "Value": "89.45"},
        {"Key": "Transaction.TimeStampYYMMDD", "Value": "2020-10-27T15:01:59+00:00"},
        {"Key": "Transaction.MerchantCardAcceptorId", "Value": "test-mid-primary"},
        {"Key": "Transaction.MerchantAcquirerBin", "Value": "3423432"},
        {"Key": "Transaction.TransactionAmount", "Value": "89.45"},
        {"Key": "Transaction.VipTransactionId", "Value": "f237df3e-c93a-4976-bdd4-ca0525ed3e20"},
        {"Key": "Transaction.VisaMerchantName", "Value": "Bink Shop"},
        {"Key": "Transaction.VisaMerchantId", "Value": "test-mid-psimi"},
        {"Key": "Transaction.VisaStoreName", "Value": "Bink Shop"},
        {"Key": "Transaction.VisaStoreId", "Value": "test-mid-secondary"},
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


@pytest.fixture
def loyalty_scheme(db_session: db.Session) -> int:
    loyalty_scheme, _ = db.get_or_create(models.LoyaltyScheme, slug="loyalty_scheme", session=db_session)
    return loyalty_scheme


@pytest.fixture
def payment_provider(db_session: db.Session) -> int:
    payment_provider, _ = db.get_or_create(models.PaymentProvider, slug="visa", session=db_session)
    return payment_provider


@pytest.fixture
def mid_primary(loyalty_scheme: LoyaltyScheme, payment_provider: PaymentProvider, db_session: db.Session) -> int:
    mid, _ = db.get_or_create(
        models.MerchantIdentifier,
        identifier="test-mid-primary",
        identifier_type=IdentifierType.PRIMARY,
        defaults={
            "loyalty_scheme": loyalty_scheme,
            "payment_provider": payment_provider,
            "location": "test",
            "postcode": "test",
        },
        session=db_session,
    )

    return mid.id


@pytest.fixture
def mid_secondary(loyalty_scheme: LoyaltyScheme, payment_provider: PaymentProvider, db_session: db.Session) -> int:
    mid, _ = db.get_or_create(
        models.MerchantIdentifier,
        identifier="test-mid-secondary",
        identifier_type=IdentifierType.SECONDARY,
        defaults={
            "loyalty_scheme": loyalty_scheme,
            "payment_provider": payment_provider,
            "location": "test",
            "postcode": "test",
        },
        session=db_session,
    )

    return mid.id


@pytest.fixture
def mid_primary_duplicate(
    loyalty_scheme: LoyaltyScheme, payment_provider: PaymentProvider, db_session: db.Session
) -> int:
    mid, _ = db.get_or_create(
        models.MerchantIdentifier,
        identifier="test-mid-primary",
        identifier_type=IdentifierType.PSIMI,
        defaults={
            "loyalty_scheme": loyalty_scheme,
            "payment_provider": payment_provider,
            "location": "test",
            "postcode": "test",
        },
        session=db_session,
    )

    return mid.id


def test_get_merchant_slug_primary_identifier_visa(mid_primary: int, db_session: db.Session):
    with mock.patch("app.db.session_scope", return_value=db_session):
        agent = VisaAuth()
        slug = agent.get_merchant_slug(visa_transaction)
        assert slug == "loyalty_scheme"


def test_get_merchant_slug_secondary_identifier_visa(mid_secondary: int, db_session: db.Session):
    with mock.patch("app.db.session_scope", return_value=db_session):
        agent = VisaAuth()
        slug = agent.get_merchant_slug(visa_transaction)
        assert slug == "loyalty_scheme"


def test_identify_mids_table_primary_identifier_visa(mid_primary: int, db_session: db.Session):
    agent = VisaAuth()
    identifer = agent._identify_mids(data, db_session)

    assert identifer == [mid_primary]


def test_identify_mids_table_secondary_identifier_visa(mid_secondary: int, db_session: db.Session):
    agent = VisaAuth()
    identifer = agent._identify_mids(data, db_session)

    assert identifer == [mid_secondary]


def test_identify_mids_table_multiple_identifiers_visa(mid_primary: int, mid_secondary: int, db_session: db.Session):
    agent = VisaAuth()
    identifer = agent._identify_mids(data, db_session)

    assert identifer == [mid_primary, mid_secondary]


def test_identify_mids_table_no_matching_identifiers_visa(db_session: db.Session):
    agent = VisaAuth()
    with pytest.raises(MissingMID) as e:
        agent._identify_mids(data, db_session)

    assert e.typename == "MissingMID"
