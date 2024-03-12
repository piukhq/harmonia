import pytest

from app import db, models
from app.unmatched_transactions.stonegate import Stonegate
from tests.fixtures import get_or_create_payment_transaction, get_or_create_transaction


@pytest.fixture
def stonegate():
    return Stonegate()


def test_find_unmatched_transactions(stonegate, db_session: db.Session) -> None:
    get_or_create_payment_transaction(session=db_session)
    transaction = get_or_create_transaction(
        session=db_session, feed_type=models.FeedType.SETTLED, merchant_slug="stonegate"
    )

    result = stonegate.find_unmatched_transactions(db_session)

    assert result == [transaction.id]
