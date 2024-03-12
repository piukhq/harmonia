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


def test_handle_transactions(stonegate, db_session: db.Session) -> None:
    transaction = get_or_create_transaction(session=db_session)
    user_identity = get_or_create_user_identity(session=db_session)
    merchant_identifier = get_or_create_merchant_identifier(session=db_session)

    result = stonegate.handle_transactions(transaction.id, db_session)

    assert result == (transaction, user_identity, merchant_identifier)


def test_update_payment_transaction_status(stonegate, db_session: db.Session) -> None:
    payment_transaction = get_or_create_payment_transaction(session=db_session)
    assert payment_transaction.status == models.TransactionStatus.PENDING

    stonegate.update_payment_transaction_status(payment_transaction.transaction_id, db_session)
    assert payment_transaction.status == models.TransactionStatus.MATCHED
