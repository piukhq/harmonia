import pendulum
import pytest

from app import db, models
from app.unmatched_transactions.stonegate import Stonegate
from tests.fixtures import (
    get_or_create_merchant_identifier,
    get_or_create_payment_transaction,
    get_or_create_transaction,
    get_or_create_user_identity,
)


@pytest.fixture
def stonegate():
    return Stonegate()


def test_find_unmatched_transactions(stonegate, db_session: db.Session) -> None:
    transaction_date = pendulum.now().subtract(days=3)
    payment_transaction = get_or_create_payment_transaction(
        session=db_session, provider_slug="amex", transaction_date=transaction_date
    )
    get_or_create_transaction(
        session=db_session,
        feed_type=models.FeedType.SETTLED,
        merchant_slug="stonegate",
        transaction_id=payment_transaction.transaction_id,
        transaction_date=transaction_date,
    )
    get_or_create_user_identity(transaction_id=payment_transaction.transaction_id, session=db_session)
    get_or_create_merchant_identifier(
        session=db_session,
        identifier_type=models.IdentifierType.PRIMARY,
        merchant_slug="stonegate",
        payment_provider_slug="amex",
    )

    for ptx, uid, mid in stonegate.find_unmatched_transactions(db_session):
        assert ptx.transaction_id == payment_transaction.transaction_id
