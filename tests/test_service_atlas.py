import pendulum
import settings

from requests.models import Response
from unittest import mock

from app.service import atlas

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

    def __init__(self, transaction_date=pendulum.now()):
        self.transaction_date = transaction_date


request_body = (
    "{"
    '"CustomerClaimTransactionRequest": {'
    '"token": "token", '
    '"customerNumber": "card_number", '
    '"id": "tx-id"'
    "}"
    "}"
)


@mock.patch("app.service.queue.add", autospec=True)
def test_queue_audit_data(mocked_queue) -> None:
    dt = pendulum.now()
    request_timestamp = pendulum.now().to_datetime_string()
    response = mock.Mock(spec=Response)
    response.json.return_value = {"outcome": "success"}
    response.status_code = 200
    response_timestamp = dt.to_datetime_string()

    atlas.queue_audit_data(
        "test-slug",
        atlas.make_audit_transactions(
            [MockMatchedTransaction(dt)], tx_loyalty_ident_callback=lambda mt: "customer-number"
        ),
        request=request_body,
        request_timestamp=request_timestamp,
        response=response,
        response_timestamp=response_timestamp,
        blob_names=["blob1", "blob2"],
    )
    mocked_queue.assert_called()

    assert mocked_queue.call_args[0][0] == {
        "provider_slug": "test-slug",
        "transactions": [
            {
                "transaction_id": 125,
                "user_id": 10,
                "spend_amount": 1500,
                "transaction_date": dt.to_datetime_string(),
                "loyalty_identifier": "customer-number",
                "record_uid": None,
            }
        ],
        "audit_data": {
            "request": {
                "body": '{"CustomerClaimTransactionRequest": {"token": '
                '"token", "customerNumber": "card_number", "id": "tx-id"}}',
                "timestamp": dt.to_datetime_string(),
            },
            "response": {"body": {"outcome": "success"}, "status_code": 200, "timestamp": dt.to_datetime_string()},
            "file_names": ["blob1", "blob2"],
        },
    }


@mock.patch("app.service.queue.add", autospec=True)
def test_queue_audit_data_non_json_response(mocked_queue) -> None:
    dt = pendulum.now()
    request_timestamp = dt.to_datetime_string()
    response = mock.Mock(spec=Response)
    response.json.side_effect = ValueError
    response.content = "some other content"
    response.status_code = 204
    response_timestamp = dt.to_datetime_string()

    atlas.queue_audit_data(
        "test-slug",
        atlas.make_audit_transactions(
            [MockMatchedTransaction(dt)], tx_loyalty_ident_callback=lambda mt: "customer-number"
        ),
        request=request_body,
        request_timestamp=request_timestamp,
        response=response,
        response_timestamp=response_timestamp,
    )
    mocked_queue.assert_called
    assert mocked_queue.call_args[0][0]["audit_data"]["response"]["body"] == "some other content"
