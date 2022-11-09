from unittest import mock

import pendulum
import pytest

from app import db, models
from app.matching.agents.generic_loyalty import GenericLoyalty
from app.matching.agents.generic_spotted import GenericSpotted
from app.models import IdentifierType
from tests.fixtures import Default, create_merchant_identifier, create_payment_transaction, create_scheme_transaction

TRANSACTION_DATE = pendulum.now()
PRIMARY_IDENTIFIER = Default.primary_identifier


@pytest.fixture
def mid_primary(db_session: db.Session) -> int:
    mid = create_merchant_identifier(
        session=db_session,
        identifier_type=IdentifierType.PRIMARY,
        merchant_slug="iceland-bonus-card",
        payment_provider_slug="amex",
    )

    return mid.id


COMMON_TX_FIELDS = dict(
    transaction_date=TRANSACTION_DATE,
    has_time=True,
    spend_amount=1699,
    spend_multiplier=100,
    spend_currency="GBP",
    first_six="123456",
    last_four="7890",
    status=models.TransactionStatus.PENDING,
    auth_code="123456",
    match_group="1234567890",
    extra_fields={},
)


@mock.patch("app.core.identifier.get_user_identity", return_value=None)
def test_make_matched_transaction_fields(mock_get_user_identity, mid_primary: int) -> None:

    ptx = create_payment_transaction(
        merchant_identifier_ids=[mid_primary],
        provider_slug="amex",
        transaction_id="test-make-matched-transaction-fields-transaction-1",
        settlement_key="1234567890",
        card_token="test-make-matched-transaction-fields-token-1",
        **COMMON_TX_FIELDS,
    )
    stx = create_scheme_transaction(
        merchant_identifier_ids=[mid_primary],
        transaction_id="test-make-matched-transaction-fields-transaction-2",
        provider_slug="iceland-bonus-card",
        payment_provider_slug="amex",
        **COMMON_TX_FIELDS,
    )

    agent = GenericLoyalty(ptx, mock_get_user_identity)
    result = agent.make_matched_transaction_fields(stx)
    assert result == {
        "merchant_identifier_id": mid_primary,
        "primary_identifier": PRIMARY_IDENTIFIER,
        "transaction_id": "test-make-matched-transaction-fields-transaction-2",
        "transaction_date": TRANSACTION_DATE,
        "spend_amount": 1699,
        "spend_multiplier": 100,
        "spend_currency": "GBP",
        "card_token": "test-make-matched-transaction-fields-token-1",
        "extra_fields": {},
    }


@mock.patch("app.core.identifier.get_user_identity", return_value=None)
def test_make_spotted_transaction_fields(mock_get_user_identity, mid_primary: int) -> None:
    ptx = create_payment_transaction(
        merchant_identifier_ids=[mid_primary],
        provider_slug="amex",
        transaction_id="test-make-spotted-transaction-fields-transaction-1",
        settlement_key="1234567890",
        card_token="test-make-spotted-transaction-fields-token-1",
        **COMMON_TX_FIELDS,
    )

    agent = GenericSpotted(ptx, mock_get_user_identity)
    result = agent.make_spotted_transaction_fields()
    assert result == {
        "merchant_identifier_id": mid_primary,
        "primary_identifier": PRIMARY_IDENTIFIER,
        "transaction_id": "test-make-spotted-transaction-fields-transaction-1",
        "transaction_date": TRANSACTION_DATE,
        "spend_amount": 1699,
        "spend_multiplier": 100,
        "spend_currency": "GBP",
        "card_token": "test-make-spotted-transaction-fields-token-1",
        "extra_fields": {},
    }
