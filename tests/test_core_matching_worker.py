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
from tests.fixtures import create_merchant_identifier

PAYMENT_PROVIDER_SLUG = "visa"
MERCHANT_SLUG = "iceland-bonus-card"


@pytest.fixture
def mid_primary(db_session: db.Session) -> int:
    mid = create_merchant_identifier(
        identifier="test-mid-primary",
        session=db_session,
        identifier_type=IdentifierType.PRIMARY,
        merchant_slug="iceland-bonus-card",
        payment_provider_slug="amex",
    )

    return mid.id


@pytest.fixture
def mid_secondary(db_session: db.Session) -> int:
    mid = create_merchant_identifier(
        identifier="test-mid-secondary",
        session=db_session,
        identifier_type=IdentifierType.PRIMARY,
        merchant_slug="iceland-bonus-card",
        payment_provider_slug="amex",
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

    logs = []
    for i in range(len(mock_logger_debug.mock_calls)):
        try:
            logs.append(mock_logger_debug.mock_calls[i].args[0])
        except IndexError:
            pass

    assert "Received 2 scheme transactions. Looking for potential matches now." in logs
    assert "Found 2 potential matching payment transactions. Enqueueing matching jobs on matching_slow queue." in logs
    assert mock_enqueue.call_count == 2
