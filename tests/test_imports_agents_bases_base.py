import pytest

from app.imports.agents.visa import VisaAuth
from app.imports.exceptions import MissingMID, MIDDataError
from app import db, models
from app.models import LoyaltyScheme, PaymentProvider

data = {
    "PRIMARY": "test-mid-primary",
    "PSIMI": "test-mid-psimi",
    "SECONDARY": "test-mid-secondary",
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


def test_get_identifier_from_mid_table_primary(mid_primary: int, db_session: db.Session):
    agent = VisaAuth()
    identifer = agent.get_identifier_from_mid_table(data, db_session)

    assert identifer == [mid_primary]


def test_get_identifier_from_mid_table_multiple(mid_primary: int, mid_secondary: int, db_session: db.Session):
    agent = VisaAuth()
    identifer = agent.get_identifier_from_mid_table(data, db_session)

    assert identifer == [mid_primary]


def test_get_identifier_from_mid_table_duplicate_identifiers(
    mid_primary: int, mid_primary_duplicate: int, db_session: db.Session
):
    agent = VisaAuth()
    with pytest.raises(MIDDataError) as e:
        agent.get_identifier_from_mid_table(data, db_session)

    assert e.typename == "MIDDataError"


def test_get_identifier_from_mid_table_no_matching_identifiers(db_session: db.Session):
    agent = VisaAuth()
    with pytest.raises(MissingMID) as e:
        agent.get_identifier_from_mid_table(data, db_session)

    assert e.typename == "MissingMID"
