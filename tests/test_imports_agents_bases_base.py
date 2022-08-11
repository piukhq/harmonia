from unittest import mock

import pytest

from app import db, models
from app.imports.agents.visa import VisaAuth
from app.imports.exceptions import MIDDataError, MissingMID
from app.models import LoyaltyScheme, PaymentProvider

pp_data = {
    "PRIMARY": "test-mid-primary",
    "PSIMI": "test-mid-psimi",
    "SECONDARY": "test-mid-secondary",
}

merchant_data = ["test-mid-primary", "test-mid-secondary"]

visa_data = {
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
        identifier_type="PRIMARY",
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
        identifier_type="SECONDARY",
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
        identifier_type="PSIMI",
        defaults={
            "loyalty_scheme": loyalty_scheme,
            "payment_provider": payment_provider,
            "location": "test",
            "postcode": "test",
        },
        session=db_session,
    )

    return mid.id


def test_get_merchant_slug_primary(mid_primary: int, db_session: db.Session):
    with mock.patch("app.db.session_scope", return_value=db_session):
        agent = VisaAuth()
        slug = agent.get_merchant_slug(visa_data)
        assert slug == "loyalty_scheme"


def test_get_merchant_slug_secondary(mid_secondary: int, db_session: db.Session):
    with mock.patch("app.db.session_scope", return_value=db_session):
        agent = VisaAuth()
        slug = agent.get_merchant_slug(visa_data)
        assert slug == "loyalty_scheme"


def test_get_identifier_from_mid_table_for_merchant_feed_primary(mid_primary: int, db_session: db.Session):
    agent = VisaAuth()
    identifer = agent.get_identifier_from_mid_table_for_merchant_feed(merchant_data, db_session)

    assert identifer == [mid_primary]


def test_get_identifier_from_mid_table_for_merchant_feed_multiple(
    mid_primary: int, mid_secondary: int, db_session: db.Session
):
    agent = VisaAuth()
    identifer = agent.get_identifier_from_mid_table_for_merchant_feed(merchant_data, db_session)

    assert identifer == [mid_primary, mid_secondary]


def test_get_identifier_from_mid_table_for_merchant_feed_no_matching_identifiers(db_session: db.Session):
    agent = VisaAuth()
    with pytest.raises(MissingMID) as e:
        agent.get_identifier_from_mid_table_for_merchant_feed(merchant_data, db_session)

    assert e.typename == "MissingMID"


def test_get_identifier_from_mid_table_for_pp_feed_primary(mid_primary: int, db_session: db.Session):
    agent = VisaAuth()
    identifer = agent.get_identifier_from_mid_table_for_payment_provider_feed(pp_data, db_session)

    assert identifer == [mid_primary]


def test_get_identifier_from_mid_table_for_pp_feed_multiple(
    mid_primary: int, mid_secondary: int, db_session: db.Session
):
    agent = VisaAuth()
    identifer = agent.get_identifier_from_mid_table_for_payment_provider_feed(pp_data, db_session)

    assert identifer == [mid_primary]


def test_get_identifier_from_mid_table_for_pp_feed_duplicate_identifiers(
    mid_primary: int, mid_primary_duplicate: int, db_session: db.Session
):
    agent = VisaAuth()
    with pytest.raises(MIDDataError) as e:
        agent.get_identifier_from_mid_table_for_payment_provider_feed(pp_data, db_session)

    assert e.typename == "MIDDataError"


def test_get_identifier_from_mid_table_for_pp_feed_no_matching_identifiers(db_session: db.Session):
    agent = VisaAuth()
    with pytest.raises(MissingMID) as e:
        agent.get_identifier_from_mid_table_for_payment_provider_feed(pp_data, db_session)

    assert e.typename == "MissingMID"
