import logging
from unittest import mock

import pendulum
import pytest
from requests.models import Response

from app.reporting import get_logger
from app.service import atlas

log = get_logger("atlas")


class MockUserIdentity:
    user_id = 10


class MockPaymentTransaction:
    user_identity = MockUserIdentity()


class MockExportTransaction:
    id = 1
    transaction_id = 125
    spend_amount = 1500
    credentials = {"card_number": "loyalty-123", "merchant_identifier": "876543"}
    mid = "1234567"
    user_id = 10
    scheme_account_id = 2
    loyalty_id = "876543"

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
def test_queue_audit_message(mocked_queue):
    dt = pendulum.now()
    request_timestamp = pendulum.now().to_datetime_string()
    response = mock.Mock(spec=Response)
    response.json.return_value = {"outcome": "success"}
    response.status_code = 200
    response_timestamp = dt.to_datetime_string()

    audit_message = atlas.make_audit_message(
        "test-slug",
        atlas.make_audit_transactions(
            [MockExportTransaction(dt)], tx_loyalty_ident_callback=lambda mt: "customer-number"
        ),
        request=request_body,
        request_timestamp=request_timestamp,
        response=response,
        response_timestamp=response_timestamp,
        blob_names=["blob1", "blob2"],
    )

    assert audit_message == {
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
    atlas.queue_audit_message(audit_message)
    mocked_queue.assert_called()
    assert mocked_queue.call_args[0][0] == audit_message


@pytest.fixture(autouse=True)
@mock.patch("app.service.queue.add", autospec=True)
def test_queue_problems_exceptions_handled(mocked_queue, caplog):
    mocked_queue.side_effect = Exception("test exception")
    log.propagate = True
    caplog.set_level(logging.WARNING)

    dt = pendulum.now()
    request_timestamp = pendulum.now().to_datetime_string()
    response = mock.Mock(spec=Response)
    response.json.return_value = {"outcome": "success"}
    response.status_code = 200
    response_timestamp = dt.to_datetime_string()

    audit_message = atlas.make_audit_message(
        "test-slug",
        atlas.make_audit_transactions(
            [MockExportTransaction(dt)], tx_loyalty_ident_callback=lambda mt: "customer-number"
        ),
        request=request_body,
        request_timestamp=request_timestamp,
        response=response,
        response_timestamp=response_timestamp,
        blob_names=["blob1", "blob2"],
    )

    with caplog.at_level(logging.WARNING):
        atlas.queue_audit_message(audit_message)
    assert "Problem during Atlas audit process" in caplog.text


def test_make_audit_message_non_json_response():
    dt = pendulum.now()
    request_timestamp = dt.to_datetime_string()
    response = mock.Mock(spec=Response)
    response.json.side_effect = ValueError
    response.text = "some other content"
    response.status_code = 204
    response_timestamp = dt.to_datetime_string()

    audit_message = atlas.make_audit_message(
        "test-slug",
        atlas.make_audit_transactions(
            [MockExportTransaction(dt)], tx_loyalty_ident_callback=lambda mt: "customer-number"
        ),
        request=request_body,
        request_timestamp=request_timestamp,
        response=response,
        response_timestamp=response_timestamp,
    )
    assert audit_message["audit_data"]["response"]["body"] == "some other content"
