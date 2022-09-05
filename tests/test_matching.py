from unittest import mock

import pendulum
import pytest
import responses

import settings
from app import db, models
from app.core import identifier
from app.core.matching_worker import MatchingWorker
from app.feeds import FeedType
from app.matching.agents.generic_spotted import GenericSpotted
from app.models import IdentifierType, UserIdentity


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
def transaction(mid_primary, mid_secondary, db_session: db.Session) -> models.Transaction:
    tx, _ = db.get_or_create(
        models.Transaction,
        feed_type=FeedType.AUTH,
        merchant_identifier_ids=[mid_primary, mid_secondary],
        primary_identifier=db_session.query(models.MerchantIdentifier)
        .filter(models.MerchantIdentifier.id == mid_primary)[0]
        .identifier,
        transaction_id="test-transaction-1",
        defaults={
            "merchant_slug": "iceland-bonus-card",
            "payment_provider_slug": "amex",
            "settlement_key": "1234567890",
            "approval_code": "",
            "card_token": "test-token-1",
            "transaction_date": pendulum.now(),
            "has_time": True,
            "spend_amount": 1699,
            "spend_multiplier": 100,
            "spend_currency": "GBP",
            "first_six": "123456",
            "last_four": "7890",
            "status": models.TransactionStatus.IMPORTED,
            "auth_code": "123456",
            "match_group": "1234567890",
        },
        session=db_session,
    )
    return tx


COMMON_TX_FIELDS = dict(
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


@responses.activate
def test_force_match_no_user_identity(mid_primary: int, db_session: db.Session) -> None:
    pcui_endpoint = f"{settings.HERMES_URL}/payment_cards/accounts/payment_card_user_info/iceland-bonus-card"
    responses.add(
        "POST",
        pcui_endpoint,
        json={},
    )

    ptx = models.PaymentTransaction(
        merchant_identifier_ids=[mid_primary],
        provider_slug="amex",
        transaction_id="test-force-match-transaction-2",
        settlement_key="1234567890",
        card_token="test-force-match-token-1",
        **COMMON_TX_FIELDS,
    )

    stx = models.SchemeTransaction(
        merchant_identifier_ids=[mid_primary],
        provider_slug="iceland-bonus-card",
        payment_provider_slug="amex",
        transaction_id="test-force-match-transaction-1",
        **COMMON_TX_FIELDS,
    )

    db_session.add(ptx)
    db_session.add(stx)
    db_session.flush()

    worker = MatchingWorker()

    with pytest.raises(MatchingWorker.RedressError):
        worker.force_match(ptx.id, stx.id, session=db_session)

    assert len(responses.calls) == 1  # should have called out to hermes once
    assert responses.calls[0].request.url == pcui_endpoint

    mtx = (
        db_session.query(models.MatchedTransaction)
        .filter(
            models.MatchedTransaction.transaction_id == stx.transaction_id,
        )
        .one_or_none()
    )
    assert mtx is None  # should be no match created


@responses.activate
def test_force_match_late_user_identity(
    mid_primary: int, transaction: models.Transaction, db_session: db.Session
) -> None:
    pcui_endpoint = f"{settings.HERMES_URL}/payment_cards/accounts/payment_card_user_info/iceland-bonus-card"
    responses.add(
        "POST",
        pcui_endpoint,
        json={
            "test-force-match-token-1": {
                "scheme_account_id": 1,
                "loyalty_id": "test",
                "user_id": 1,
                "credentials": "test",
                "card_information": {
                    "first_six": "123456",
                    "last_four": "7890",
                },
            },
        },
    )

    ptx = models.PaymentTransaction(
        merchant_identifier_ids=[mid_primary],
        provider_slug="amex",
        transaction_id="test-force-match-transaction-2",
        settlement_key="1234567890",
        card_token="test-force-match-token-1",
        **COMMON_TX_FIELDS,
    )

    stx = models.SchemeTransaction(
        merchant_identifier_ids=[mid_primary],
        provider_slug="iceland-bonus-card",
        payment_provider_slug="amex",
        transaction_id="test-force-match-transaction-1",
        **COMMON_TX_FIELDS,
    )

    db_session.add(ptx)
    db_session.add(stx)
    db_session.flush()

    worker = MatchingWorker()

    user_identity = identifier.try_get_user_identity(ptx.transaction_id, session=db_session)
    assert user_identity is None  # payment transaction should have no user identity to begin with

    worker.force_match(ptx.id, stx.id, session=db_session)

    user_identity = identifier.try_get_user_identity(ptx.transaction_id, session=db_session)
    assert user_identity is not None  # payment transaction should now have a user identity

    assert len(responses.calls) == 1  # should have called out to hermes once
    assert responses.calls[0].request.url == pcui_endpoint

    mtx = (
        db_session.query(models.MatchedTransaction)
        .filter(
            models.MatchedTransaction.transaction_id == stx.transaction_id,
        )
        .one_or_none()
    )
    assert mtx is not None  # should have created a match


@responses.activate
def test_force_match_hermes_down(mid_primary: int, db_session: db.Session) -> None:
    """
    By not adding the request via `responses.add` we can simulate hermes being unavailable.
    """
    pcui_endpoint = f"{settings.HERMES_URL}/payment_cards/accounts/payment_card_user_info/iceland-bonus-card"

    ptx = models.PaymentTransaction(
        merchant_identifier_ids=[mid_primary],
        provider_slug="amex",
        transaction_id="test-force-match-transaction-2",
        settlement_key="1234567890",
        card_token="test-force-match-token-1",
        **COMMON_TX_FIELDS,
    )

    stx = models.SchemeTransaction(
        merchant_identifier_ids=[mid_primary],
        provider_slug="iceland-bonus-card",
        payment_provider_slug="amex",
        transaction_id="test-force-match-transaction-1",
        **COMMON_TX_FIELDS,
    )

    db_session.add(ptx)
    db_session.add(stx)
    db_session.flush()

    worker = MatchingWorker()

    with pytest.raises(MatchingWorker.RedressError):
        worker.force_match(ptx.id, stx.id, session=db_session)

    assert len(responses.calls) == 1  # should have called out to hermes once
    assert responses.calls[0].request.url == pcui_endpoint

    mtx = (
        db_session.query(models.MatchedTransaction)
        .filter(
            models.MatchedTransaction.transaction_id == stx.transaction_id,
        )
        .one_or_none()
    )
    assert mtx is None  # should be no match created


@mock.patch("app.registry.Registry.instantiate", return_value=None)
@mock.patch("app.core.identifier.get_user_identity", return_value=None)
def test_get_agent_for_payment_transaction_multiple_mids(
    mock_get_user_identity, mock_instantiate, mid_primary: int, mid_secondary: int, db_session: db.Session
) -> None:
    ptx = models.PaymentTransaction(
        merchant_identifier_ids=[mid_primary, mid_secondary],
        provider_slug="amex",
        transaction_id="test-single-primary-mid-transaction-2",
        settlement_key="1234567890",
        card_token="test-single-primary-mid-token-1",
        **COMMON_TX_FIELDS,
    )
    worker = MatchingWorker()
    worker._get_agent_for_payment_transaction(payment_transaction=ptx, session=db_session)
    assert mock_instantiate.call_args[0][0] == "iceland-bonus-card"


def test_get_primary_identifier_from_transaction(
    mid_primary: int, mid_secondary: int, transaction: models.Transaction, db_session: db.Session
) -> None:
    # tx, _ = db.get_or_create(
    #     models.Transaction,
    #     feed_type=FeedType.AUTH,
    #     merchant_identifier_ids=[mid_primary, mid_secondary],
    #     primary_identifier=db_session.query(models.MerchantIdentifier)
    #     .filter(models.MerchantIdentifier.id == mid_primary)[0]
    #     .identifier,
    #     transaction_id="test-single-primary-mid-transaction-1",
    #     defaults={
    #         "merchant_slug": "iceland-bonus-card",
    #         "payment_provider_slug": "amex",
    #         "settlement_key": "1234567890",
    #         "approval_code": "",
    #         "card_token": "test-single-primary-mid-token-1",
    #         "transaction_date": pendulum.now(),
    #         "has_time": True,
    #         "spend_amount": 1699,
    #         "spend_multiplier": 100,
    #         "spend_currency": "GBP",
    #         "first_six": "123456",
    #         "last_four": "7890",
    #         "status": models.TransactionStatus.IMPORTED,
    #         "auth_code": "123456",
    #         "match_group": "1234567890",
    #     },
    #     session=db_session,
    # )

    ptx = models.PaymentTransaction(
        merchant_identifier_ids=[mid_primary, mid_secondary],
        provider_slug="amex",
        transaction_id="test-single-primary-mid-transaction-2",
        settlement_key="1234567890",
        card_token="test-single-primary-mid-token-1",
        **COMMON_TX_FIELDS,
    )

    user_id = UserIdentity()
    agent = GenericSpotted(payment_transaction=ptx, user_identity=user_id)
    agent.payment_transaction = ptx
    primary_id = agent._get_primary_identifier_from_transaction(session=db_session)

    assert primary_id == mid_primary
