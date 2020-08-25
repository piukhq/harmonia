import pendulum
import pytest
import settings

from requests.models import Response
from unittest import mock

from app.service.atlas import Atlas

# this allows the atlas service to work normally.
settings.SIMULATE_EXPORTS = False


class MockUserIdentity:
    user_id = 10


class MockPaymentTransaction:
    user_identity = MockUserIdentity()


class MockMatchedTransaction:
    id = 1
    transaction_id = 125
    payment_transaction = MockPaymentTransaction()
    spend_amount = 1500
    transaction_date = pendulum.now()


@pytest.fixture
def atlas() -> Atlas:
    return Atlas()


request_body = (
    "{"
    '"CustomerClaimTransactionRequest": {'
    '"token": "token",'
    '"customerNumber": credentials["card_number"],'
    '"id": matched_transaction.transaction_id,'
    "}"
    "}"
)


@mock.patch("app.service.queue.add", autospec=True)
def test_save_transaction(mocked_queue) -> None:
    atlas = Atlas()
    response = mock.Mock(spec=Response)
    response.json.return_value = {"outcome": "success"}
    response.status_code = 200

    atlas.save_transaction("test-slug", response, request_body, [MockMatchedTransaction()])
    mocked_queue.assert_called
