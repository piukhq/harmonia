from unittest import mock

import pendulum
import pytest

from app import db, models
from app.matching.agents.generic_loyalty import GenericLoyalty
from app.models import IdentifierType


@pytest.fixture
def mid_primary(db_session: db.Session) -> int:
    loyalty_scheme, _ = db.get_or_create(models.LoyaltyScheme, slug="iceland-bonus-card", session=db_session)
    payment_provider, _ = db.get_or_create(models.PaymentProvider, slug="amex", session=db_session)
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
def mid_secondary(db_session: db.Session) -> int:
    loyalty_scheme, _ = db.get_or_create(models.LoyaltyScheme, slug="iceland-bonus-card", session=db_session)
    payment_provider, _ = db.get_or_create(models.PaymentProvider, slug="amex", session=db_session)
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
def mid_psimi(db_session: db.Session) -> int:
    loyalty_scheme, _ = db.get_or_create(models.LoyaltyScheme, slug="iceland-bonus-card", session=db_session)
    payment_provider, _ = db.get_or_create(models.PaymentProvider, slug="amex", session=db_session)
    mid, _ = db.get_or_create(
        models.MerchantIdentifier,
        identifier="test-mid-psimi",
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


@mock.patch("app.core.identifier.get_user_identity", return_value=None)
def test_get_mid_used_for_identification(
    mock_get_user_identity, mid_primary: int, mid_secondary: int, mid_psimi: int, db_session: db.Session
) -> None:
    merchant_identifier_ids = [mid_secondary, mid_psimi]
    ptx = models.PaymentTransaction(
        merchant_identifier_ids=merchant_identifier_ids,
        provider_slug="amex",
        transaction_id="test-get-mid-used-for-identification-transaction-1",
        settlement_key="1234567890",
        card_token="test-get-mid-used-for-identification-token-1",
        transaction_date=pendulum.now(),
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
    agent = GenericLoyalty(ptx, mock_get_user_identity)
    result = agent.get_priority_mid_used_for_identification(merchant_identifier_ids, db_session)
    assert result == "test-mid-secondary"
