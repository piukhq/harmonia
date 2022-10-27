from unittest import mock

import pytest

from app import db, models
from app.feeds import FeedType
from app.imports.agents.bases.base import IdentifyArgs, identify_mids
from app.imports.agents.visa import VisaAuth
from app.imports.exceptions import MissingMID
from app.models import IdentifierType, LoyaltyScheme, PaymentProvider, TransactionStatus

data = [
    (IdentifierType.PRIMARY, "test-mid-primary"),
    (IdentifierType.SECONDARY, "test-mid-secondary"),
    (IdentifierType.PSIMI, "test-mid-psimi"),
]

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


def test_identify_mids_primary_identifier_visa(mid_primary: int, db_session: db.Session):
    agent = VisaAuth()
    identifer = agent._identify_mids(data, db_session)

    assert identifer == [mid_primary]


def test_identify_mids_secondary_identifier_visa(mid_secondary: int, db_session: db.Session):
    agent = VisaAuth()
    identifer = agent._identify_mids(data, db_session)

    assert identifer == [mid_secondary]


def test_identify_mids_multiple_identifiers_visa(mid_secondary: int, mid_primary: int, db_session: db.Session):
    agent = VisaAuth()
    identifer = agent._identify_mids(data, db_session)

    assert identifer == [mid_primary]


def test_identify_mids_multiple_identifiers(mid_secondary: int, mid_primary: int, db_session: db.Session):
    mids = [
        (IdentifierType.SECONDARY, "test-mid-secondary"),
        (IdentifierType.PSIMI, "test-mid-psimi"),
        (IdentifierType.PRIMARY, "test-mid-primary"),
    ]
    provider_slug = "visa"
    identifer_dict = identify_mids(*mids, provider_slug=provider_slug, session=db_session)

    assert identifer_dict == {IdentifierType.SECONDARY.value: mid_secondary, IdentifierType.PRIMARY.value: mid_primary}


def test_identify_mids_no_matching_identifiers_visa(db_session: db.Session):
    agent = VisaAuth()
    with pytest.raises(MissingMID) as e:
        agent._identify_mids(data, db_session)

    assert e.typename == "MissingMID"


def test_build_inserts(mid_primary: int, mid_secondary: int, db_session: db.Session):
    match_group = "da34aa2a4abf4cc190c3519f7c6e2f88"
    source = "AMQP: visa-auth"

    agent = VisaAuth()
    import_transaction_insert, transaction_insert, identify = agent._build_inserts(
        tx_data=visa_transaction, match_group=match_group, source=source, session=db_session
    )

    assert import_transaction_insert == {
        "transaction_id": "f237df3e-c93a-4976-bdd4-ca0525ed3e20",
        "feed_type": FeedType.AUTH,
        "provider_slug": "visa",
        "identified": True,
        "match_group": "da34aa2a4abf4cc190c3519f7c6e2f88",
        "data": visa_transaction,
        "source": "AMQP: visa-auth",
    }
    assert transaction_insert == {
        "feed_type": FeedType.AUTH,
        "status": TransactionStatus.IMPORTED,
        "merchant_identifier_ids": [mid_primary],
        "transaction_id": "f237df3e-c93a-4976-bdd4-ca0525ed3e20",
        "match_group": "da34aa2a4abf4cc190c3519f7c6e2f88",
        "merchant_slug": "loyalty_scheme",
        "payment_provider_slug": "visa",
        "primary_identifier": "test-mid-primary",
        "transaction_date": agent.pendulum_parse("2020-10-27T15:01:59+00:00", tz="GMT"),
        "has_time": True,
        "spend_amount": 8945,
        "spend_multiplier": 100,
        "spend_currency": "GBP",
        "card_token": "token-123",
        "settlement_key": "1d5d6772aa6be73dc2c76287de2c1429ef56259aa7e2c193613105304772b989",
        "first_six": None,
        "last_four": None,
        "auth_code": "444444",
        "approval_code": "",
    }
    assert identify == IdentifyArgs(
        transaction_id="f237df3e-c93a-4976-bdd4-ca0525ed3e20",
        merchant_identifier_ids=[mid_primary],
        card_token="token-123",
    )
