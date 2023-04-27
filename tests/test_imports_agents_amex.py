from unittest import mock

import pendulum
import pytest

from app import db, models
from app.imports.agents.amex import AmexAuth, AmexSettlement
from tests.fixtures import Default, SampleTransactions, get_or_create_merchant_identifier

PAYMENT_PROVIDER_SLUG = "amex"

ICELAND_SLUG = "iceland-bonus-card"
ICELAND_IDENTIFIER = "iceland_mid"
SQUAREMEAL_SLUG = "squaremeal"
SQUAREMEAL_IDENTIFIER = "squaremeal_mid"


@pytest.fixture
def iceland_mid(db_session: db.Session) -> models.MerchantIdentifier:
    return get_or_create_merchant_identifier(
        session=db_session,
        identifier=ICELAND_IDENTIFIER,
        merchant_slug=ICELAND_SLUG,
        payment_provider_slug=PAYMENT_PROVIDER_SLUG,
    )


@pytest.fixture
def squaremeal_mid(db_session: db.Session) -> models.MerchantIdentifier:
    return get_or_create_merchant_identifier(
        session=db_session,
        identifier=SQUAREMEAL_IDENTIFIER,
        merchant_slug=SQUAREMEAL_SLUG,
        payment_provider_slug=PAYMENT_PROVIDER_SLUG,
    )


def test_auth_do_not_import_streaming_agent():
    should_import = AmexAuth().do_not_import(SQUAREMEAL_SLUG)
    assert should_import is True


def test_auth_do_not_import_matching_agent():
    should_import = AmexAuth().do_not_import("wasabi")
    assert should_import is False


def test_auth_to_transaction_fields_streaming_agent(squaremeal_mid: models.MerchantIdentifier, db_session: db.Session):
    with mock.patch("app.imports.agents.bases.base.db.session_scope", return_value=db_session):
        transaction_fields = AmexAuth().to_transaction_fields(
            SampleTransactions().amex_auth(identifier=SQUAREMEAL_IDENTIFIER)
        )

    assert transaction_fields is None


def test_auth_to_transaction_fields_matching_agent(iceland_mid: models.MerchantIdentifier, db_session: db.Session):
    with mock.patch("app.imports.agents.bases.base.db.session_scope", return_value=db_session):
        transaction_fields = AmexAuth().to_transaction_fields(
            SampleTransactions().amex_auth(identifier=ICELAND_IDENTIFIER)
        )

    assert transaction_fields._asdict() == {
        "merchant_slug": ICELAND_SLUG,
        "payment_provider_slug": PAYMENT_PROVIDER_SLUG,
        "transaction_date": pendulum.DateTime(2022, 11, 4, 8, 55, 50, tzinfo=pendulum.timezone("MST")),
        "has_time": True,
        "spend_amount": 5566,
        "spend_multiplier": 100,
        "spend_currency": "GBP",
        "card_token": "CqN58fD9MI1s7ePn0M5F1RxRu1P",
        "settlement_key": "Qzg0Q0FBQzctRTJDMS00RUFGLTkyQTEtRTRDQzZEMEI1MTk5",
        "first_six": None,
        "last_four": None,
        "auth_code": "",
        "approval_code": "472624",
        "extra_fields": None,
    }


def test_auth_get_transaction_id():
    transaction_id = AmexAuth().get_transaction_id(SampleTransactions().amex_auth())
    assert transaction_id == "Qzg0Q0FBQzctRTJDMS00RUFGLTkyQTEtRTRDQzZEMEI1MTk5"


def test_auth_get_mids():
    ids = AmexAuth().get_mids(SampleTransactions().amex_auth())
    assert ids == [(models.IdentifierType.PRIMARY, Default.primary_identifier)]


def test_settlement_to_transaction_fields_with_dpan(iceland_mid: models.MerchantIdentifier, db_session: db.Session):
    with mock.patch("app.imports.agents.bases.base.db.session_scope", return_value=db_session):
        transaction_fields = AmexSettlement().to_transaction_fields(
            SampleTransactions().amex_settlement(identifier=ICELAND_IDENTIFIER)
        )

    assert transaction_fields._asdict() == {
        "merchant_slug": ICELAND_SLUG,
        "payment_provider_slug": PAYMENT_PROVIDER_SLUG,
        "transaction_date": pendulum.DateTime(2022, 11, 4, 15, 55, 50, tzinfo=pendulum.timezone("Europe/London")),
        "has_time": True,
        "spend_amount": 5566,
        "spend_multiplier": 100,
        "spend_currency": "GBP",
        "card_token": "CqN58fD9MI1s7ePn0M5F1RxRu1P",
        "settlement_key": "NUE3QTUyNzktMDFEMi00ODQwLUI5NDItRTkzQjMwNUQ0QTBB",
        "first_six": "123456",
        "last_four": "7890",
        "auth_code": "",
        "approval_code": "472624",
        "extra_fields": None,
    }


def test_settlement_to_transaction_fields_without_dpan(iceland_mid: models.MerchantIdentifier, db_session: db.Session):
    transaction = SampleTransactions().amex_settlement(identifier=ICELAND_IDENTIFIER)
    transaction["dpan"] = ""
    with mock.patch("app.imports.agents.bases.base.db.session_scope", return_value=db_session):
        transaction_fields = AmexSettlement().to_transaction_fields(transaction)

    assert transaction_fields._asdict() == {
        "merchant_slug": ICELAND_SLUG,
        "payment_provider_slug": PAYMENT_PROVIDER_SLUG,
        "transaction_date": pendulum.DateTime(2022, 11, 4, 15, 55, 50, tzinfo=pendulum.timezone("Europe/London")),
        "has_time": True,
        "spend_amount": 5566,
        "spend_multiplier": 100,
        "spend_currency": "GBP",
        "card_token": "CqN58fD9MI1s7ePn0M5F1RxRu1P",
        "settlement_key": "NUE3QTUyNzktMDFEMi00ODQwLUI5NDItRTkzQjMwNUQ0QTBB",
        "first_six": None,
        "last_four": None,
        "auth_code": "",
        "approval_code": "472624",
        "extra_fields": None,
    }


def test_settlement_get_transaction_id():
    transaction_id = AmexSettlement().get_transaction_id(SampleTransactions().amex_settlement())
    assert transaction_id == "NUE3QTUyNzktMDFEMi00ODQwLUI5NDItRTkzQjMwNUQ0QTBB"


def test_settlement_get_mids():
    ids = AmexSettlement().get_mids(SampleTransactions().amex_settlement())
    assert ids == [(models.IdentifierType.PRIMARY, Default.primary_identifier)]
