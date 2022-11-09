from unittest import mock

import pytest

from app import db
from app.feeds import FeedType
from app.imports.agents.bases.base import IdentifyArgs, identify_mids
from app.imports.agents.visa import VisaAuth
from app.imports.exceptions import MissingMID
from app.models import IdentifierType, TransactionStatus
from tests.fixtures import Default, SampleTransactions, get_or_create_merchant_identifier

TRANSACTION_ID = "f237df3e-c93a-4976-bdd4-ca0525ed3e20"
PRIMARY_IDENTIFIER = Default.primary_identifier
SECONDARY_IDENTIFIER = Default.secondary_identifier
MERCHANT_SLUG = Default.merchant_slug
PAYMENT_PROVIDER_SLUG = "visa"

DATA = [
    (IdentifierType.PRIMARY, PRIMARY_IDENTIFIER),
    (IdentifierType.SECONDARY, SECONDARY_IDENTIFIER),
    (IdentifierType.PSIMI, Default.psimi_identifier),
]

VISA_TRANSACTION = SampleTransactions().visa_auth(
    transaction_id=TRANSACTION_ID,
)


@pytest.fixture
def mid_primary(db_session: db.Session) -> int:
    mid = get_or_create_merchant_identifier(
        session=db_session,
        payment_provider_slug=PAYMENT_PROVIDER_SLUG,
    )

    return mid.id


@pytest.fixture
def mid_secondary(db_session: db.Session) -> int:
    mid = get_or_create_merchant_identifier(
        session=db_session,
        identifier=SECONDARY_IDENTIFIER,
        identifier_type=IdentifierType.SECONDARY,
        payment_provider_slug=PAYMENT_PROVIDER_SLUG,
    )
    return mid.id


# TODO: this isn't used, but should be to test this edge case
@pytest.fixture
def mid_primary_duplicate(db_session: db.Session) -> int:
    mid = get_or_create_merchant_identifier(
        session=db_session,
        identifier_type=IdentifierType.PSIMI,
        merchant_slug=MERCHANT_SLUG,
        payment_provider_slug=PAYMENT_PROVIDER_SLUG,
    )
    return mid.id


def test_get_merchant_slug_primary_identifier_visa(mid_primary: int, db_session: db.Session):
    with mock.patch("app.db.session_scope", return_value=db_session):
        agent = VisaAuth()
        slug = agent.get_merchant_slug(VISA_TRANSACTION)
        assert slug == MERCHANT_SLUG


def test_get_merchant_slug_secondary_identifier_visa(mid_secondary: int, db_session: db.Session):
    with mock.patch("app.db.session_scope", return_value=db_session):
        agent = VisaAuth()
        slug = agent.get_merchant_slug(VISA_TRANSACTION)
        assert slug == MERCHANT_SLUG


def test_identify_mids_primary_identifier_visa(mid_primary: int, db_session: db.Session):
    agent = VisaAuth()
    identifer = agent._identify_mids(DATA, db_session)

    assert identifer == [mid_primary]


def test_identify_mids_secondary_identifier_visa(mid_secondary: int, db_session: db.Session):
    agent = VisaAuth()
    identifer = agent._identify_mids(DATA, db_session)

    assert identifer == [mid_secondary]


def test_identify_mids_multiple_identifiers_visa(mid_secondary: int, mid_primary: int, db_session: db.Session):
    agent = VisaAuth()
    identifer = agent._identify_mids(DATA, db_session)

    assert identifer == [mid_primary]


def test_identify_mids_multiple_identifiers(mid_secondary: int, mid_primary: int, db_session: db.Session):
    mids = DATA
    provider_slug = PAYMENT_PROVIDER_SLUG
    identifer_dict = identify_mids(*mids, provider_slug=provider_slug, session=db_session)

    assert identifer_dict == {IdentifierType.SECONDARY.value: mid_secondary, IdentifierType.PRIMARY.value: mid_primary}


def test_identify_mids_no_matching_identifiers_visa(db_session: db.Session):
    agent = VisaAuth()
    with pytest.raises(MissingMID) as e:
        agent._identify_mids(DATA, db_session)

    assert e.typename == "MissingMID"


@mock.patch("app.imports.agents.bases.base.get_merchant_slug", return_value=MERCHANT_SLUG)
def test_build_inserts(mock_get_merchant_slug, mid_primary: int, mid_secondary: int, db_session: db.Session):
    match_group = "da34aa2a4abf4cc190c3519f7c6e2f88"
    source = "AMQP: visa-auth"

    agent = VisaAuth()
    import_transaction_insert, transaction_insert, identify = agent._build_inserts(
        tx_data=VISA_TRANSACTION, match_group=match_group, source=source, session=db_session
    )

    assert import_transaction_insert == {
        "transaction_id": TRANSACTION_ID,
        "feed_type": FeedType.AUTH,
        "provider_slug": PAYMENT_PROVIDER_SLUG,
        "identified": True,
        "match_group": "da34aa2a4abf4cc190c3519f7c6e2f88",
        "data": VISA_TRANSACTION,
        "source": "AMQP: visa-auth",
    }
    assert transaction_insert == {
        "feed_type": FeedType.AUTH,
        "status": TransactionStatus.IMPORTED,
        "merchant_identifier_ids": [mid_primary],
        "transaction_id": TRANSACTION_ID,
        "match_group": "da34aa2a4abf4cc190c3519f7c6e2f88",
        "merchant_slug": MERCHANT_SLUG,
        "payment_provider_slug": PAYMENT_PROVIDER_SLUG,
        "primary_identifier": PRIMARY_IDENTIFIER,
        "transaction_date": Default.transaction_date.replace(microsecond=0),
        "has_time": True,
        "spend_amount": int(Default.spend_amount * Default.spend_multiplier),
        "spend_multiplier": Default.spend_multiplier,
        "spend_currency": "GBP",
        "card_token": Default.user_token,
        "settlement_key": "1d5d6772aa6be73dc2c76287de2c1429ef56259aa7e2c193613105304772b989",
        "first_six": None,
        "last_four": None,
        "auth_code": Default.auth_code,
        "approval_code": "",
    }
    assert identify == IdentifyArgs(
        transaction_id=TRANSACTION_ID,
        merchant_identifier_ids=[mid_primary],
        card_token=Default.user_token,
    )
