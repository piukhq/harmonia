import uuid
from unittest import mock

import pendulum
import pytest
import responses

import settings
from app import db, models
from app.core import identifier
from app.core.matching_worker import MatchingWorker
from app.feeds import FeedType
from app.models import IdentifierType

PAYMENT_PROVIDER_SLUG = "visa"
MERCHANT_SLUG = "iceland-bonus-card"


@pytest.fixture
def mid_primary(db_session: db.Session) -> int:
    loyalty_scheme, _ = db.get_or_create(models.LoyaltyScheme, slug=MERCHANT_SLUG, session=db_session)
    payment_provider, _ = db.get_or_create(models.PaymentProvider, slug=PAYMENT_PROVIDER_SLUG, session=db_session)
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
    loyalty_scheme, _ = db.get_or_create(models.LoyaltyScheme, slug=MERCHANT_SLUG, session=db_session)
    payment_provider, _ = db.get_or_create(models.PaymentProvider, slug=PAYMENT_PROVIDER_SLUG, session=db_session)
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
            "merchant_slug": MERCHANT_SLUG,
            "payment_provider_slug": PAYMENT_PROVIDER_SLUG,
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
    primary_identifier="test-mid-primary",
)


def create_scheme_transaction_record(
    session: db.Session,
    merchant_identifier_ids: list[int],
    primary_identifier: str,
    provider_slug: str,
    payment_provider_slug: str,
    transaction_id: str,
    transaction_date: pendulum.DateTime,
    spend_amount: int,
    spend_multiplier: int,
    spend_currency: str,
    **kwargs,
) -> None:
    db.get_or_create(
        models.SchemeTransaction,
        transaction_id=transaction_id,
        defaults=dict(
            merchant_identifier_ids=merchant_identifier_ids,
            primary_identifier=primary_identifier,
            provider_slug=provider_slug,
            payment_provider_slug=payment_provider_slug,
            transaction_date=transaction_date,
            spend_amount=spend_amount,
            spend_multiplier=spend_multiplier,
            spend_currency=spend_currency,
            **kwargs,
        ),
        session=session,
    )


def create_payment_transaction_record(
    session: db.Session,
    merchant_identifier_ids: list[int],
    primary_identifier: str,
    provider_slug: str,
    transaction_id: str,
    transaction_date: pendulum.DateTime,
    spend_amount: int,
    spend_multiplier: int,
    spend_currency: str,
    card_token: str,
    **kwargs,
) -> None:
    db.get_or_create(
        models.PaymentTransaction,
        transaction_id=transaction_id,
        defaults=dict(
            merchant_identifier_ids=merchant_identifier_ids,
            primary_identifier=primary_identifier,
            provider_slug=provider_slug,
            transaction_date=transaction_date,
            spend_amount=spend_amount,
            spend_multiplier=spend_multiplier,
            spend_currency=spend_currency,
            card_token=card_token,
            **kwargs,
        ),
        session=session,
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
        provider_slug=PAYMENT_PROVIDER_SLUG,
        transaction_id="test-force-match-transaction-2",
        settlement_key="1234567890",
        card_token="test-force-match-token-1",
        **COMMON_TX_FIELDS,
    )

    stx = models.SchemeTransaction(
        merchant_identifier_ids=[mid_primary],
        provider_slug=MERCHANT_SLUG,
        payment_provider_slug=PAYMENT_PROVIDER_SLUG,
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
        provider_slug=PAYMENT_PROVIDER_SLUG,
        transaction_id="test-force-match-transaction-2",
        settlement_key="1234567890",
        card_token="test-force-match-token-1",
        **COMMON_TX_FIELDS,
    )

    stx = models.SchemeTransaction(
        merchant_identifier_ids=[mid_primary],
        provider_slug=MERCHANT_SLUG,
        payment_provider_slug=PAYMENT_PROVIDER_SLUG,
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
        provider_slug=PAYMENT_PROVIDER_SLUG,
        transaction_id="test-force-match-transaction-2",
        settlement_key="1234567890",
        card_token="test-force-match-token-1",
        **COMMON_TX_FIELDS,
    )

    stx = models.SchemeTransaction(
        merchant_identifier_ids=[mid_primary],
        provider_slug=MERCHANT_SLUG,
        payment_provider_slug=PAYMENT_PROVIDER_SLUG,
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
    mock_get_user_identity, mock_instantiate, mid_primary: int, db_session: db.Session
) -> None:
    ptx = models.PaymentTransaction(
        merchant_identifier_ids=[mid_primary],
        provider_slug=PAYMENT_PROVIDER_SLUG,
        transaction_id="test-single-primary-mid-transaction-2",
        settlement_key="1234567890",
        card_token="test-single-primary-mid-token-1",
        **COMMON_TX_FIELDS,
    )
    worker = MatchingWorker()
    worker._get_agent_for_payment_transaction(payment_transaction=ptx, session=db_session)
    assert mock_instantiate.call_args[0][0] == MERCHANT_SLUG


@mock.patch("app.tasks.LoggedQueue.enqueue")
@mock.patch("app.core.matching_worker.get_logger")
def test_handle_scheme_transactions_multiple_payment_transaction_mids(
    mock_logger_debug, mock_enqueue, mid_primary, mid_secondary, db_session: db.Session
) -> None:
    match_group = "73e3a7b5-48df-4b0b-bdfd-a64d79337eb4"

    COMMON = dict(
        transaction_date=pendulum.now(),
        spend_multiplier=100,
        spend_currency="GBP",
    )

    create_payment_transaction_record(
        session=db_session,
        merchant_identifier_ids=[mid_primary],
        primary_identifier="test_mid_primary_1",
        provider_slug=PAYMENT_PROVIDER_SLUG,
        transaction_id="ptx1_id",
        spend_amount=2400,
        card_token="ptx1_token",
        match_group=uuid.uuid4(),
        **COMMON,
    )

    create_payment_transaction_record(
        session=db_session,
        merchant_identifier_ids=[mid_secondary],
        primary_identifier="test_mid_primary_2",
        provider_slug="visa",
        transaction_id="ptx2_id",
        spend_amount=1300,
        card_token="ptx2_token",
        match_group=uuid.uuid4(),
        **COMMON,
    )

    create_scheme_transaction_record(
        session=db_session,
        merchant_identifier_ids=[],
        primary_identifier="test_mid_primary_1",
        provider_slug=MERCHANT_SLUG,
        payment_provider_slug="visa",
        transaction_id="stx1_id",
        spend_amount=2400,
        match_group=match_group,
        **COMMON,
    )

    create_scheme_transaction_record(
        session=db_session,
        merchant_identifier_ids=[],
        primary_identifier="test_mid_primary_2",
        provider_slug=MERCHANT_SLUG,
        payment_provider_slug="visa",
        transaction_id="stx2_id",
        spend_amount=1300,
        match_group=match_group,
        **COMMON,
    )

    worker = MatchingWorker()
    worker.handle_scheme_transactions(match_group, session=db_session)

    logs = [mock_logger_debug.mock_calls[2].args[0], mock_logger_debug.mock_calls[3].args[0]]

    assert "Received 2 scheme transactions. Looking for potential matches now." in logs
    assert "Found 2 potential matching payment transactions. Enqueueing matching jobs on matching_slow queue." in logs
    mock_enqueue.call_count == 2
