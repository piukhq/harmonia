import pytest
import pendulum
import responses

from app import db, models
from app.core.matching_worker import MatchingWorker
import settings


@pytest.fixture
def mid(db_session: db.Session) -> int:
    loyalty_scheme = models.LoyaltyScheme(slug="iceland-bonus-card")
    payment_provider = models.PaymentProvider(slug="amex")
    mid = models.MerchantIdentifier(
        mid="test-force-match-mid-1",
        store_id=None,
        loyalty_scheme=loyalty_scheme,
        payment_provider=payment_provider,
        location="test",
        postcode="test",
    )

    db_session.add(loyalty_scheme)
    db_session.add(payment_provider)
    db_session.add(mid)
    db_session.flush()

    return mid.id


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
def test_force_match_no_user_identity(mid: int, db_session: db.Session) -> None:
    pcui_endpoint = f"{settings.HERMES_URL}/payment_cards/accounts/payment_card_user_info/iceland-bonus-card"
    responses.add(
        "POST",
        pcui_endpoint,
        json={},
    )

    ptx = models.PaymentTransaction(
        merchant_identifier_ids=[mid],
        provider_slug="amex",
        transaction_id="test-force-match-transaction-2",
        settlement_key="1234567890",
        card_token="test-force-match-token-1",
        user_identity_id=None,
        **COMMON_TX_FIELDS,
    )

    stx = models.SchemeTransaction(
        merchant_identifier_ids=[mid],
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
            models.MatchedTransaction.payment_transaction_id == ptx.id,
            models.MatchedTransaction.scheme_transaction_id == stx.id,
        )
        .one_or_none()
    )
    assert mtx is None  # should be no match created


@responses.activate
def test_force_match_late_user_identity(mid: int, db_session: db.Session) -> None:
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
        merchant_identifier_ids=[mid],
        provider_slug="amex",
        transaction_id="test-force-match-transaction-2",
        settlement_key="1234567890",
        card_token="test-force-match-token-1",
        user_identity_id=None,
        **COMMON_TX_FIELDS,
    )

    stx = models.SchemeTransaction(
        merchant_identifier_ids=[mid],
        provider_slug="iceland-bonus-card",
        payment_provider_slug="amex",
        transaction_id="test-force-match-transaction-1",
        **COMMON_TX_FIELDS,
    )

    db_session.add(ptx)
    db_session.add(stx)
    db_session.flush()

    worker = MatchingWorker()

    assert ptx.user_identity_id is None  # payment transaction should have no user identity to begin with

    worker.force_match(ptx.id, stx.id, session=db_session)

    assert ptx.user_identity_id is not None  # payment transaction should now have a user identity

    assert len(responses.calls) == 1  # should have called out to hermes once
    assert responses.calls[0].request.url == pcui_endpoint

    mtx = (
        db_session.query(models.MatchedTransaction)
        .filter(
            models.MatchedTransaction.payment_transaction_id == ptx.id,
            models.MatchedTransaction.scheme_transaction_id == stx.id,
        )
        .one_or_none()
    )
    assert mtx is not None  # should have created a match


@responses.activate
def test_force_match_hermes_down(mid: int, db_session: db.Session) -> None:
    """
    By not adding the request via `responses.add` we can simulate hermes being unavailable.
    """
    pcui_endpoint = f"{settings.HERMES_URL}/payment_cards/accounts/payment_card_user_info/iceland-bonus-card"

    ptx = models.PaymentTransaction(
        merchant_identifier_ids=[mid],
        provider_slug="amex",
        transaction_id="test-force-match-transaction-2",
        settlement_key="1234567890",
        card_token="test-force-match-token-1",
        user_identity_id=None,
        **COMMON_TX_FIELDS,
    )

    stx = models.SchemeTransaction(
        merchant_identifier_ids=[mid],
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
            models.MatchedTransaction.payment_transaction_id == ptx.id,
            models.MatchedTransaction.scheme_transaction_id == stx.id,
        )
        .one_or_none()
    )
    assert mtx is None  # should be no match created
