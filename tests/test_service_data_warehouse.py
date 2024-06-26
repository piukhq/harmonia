from unittest import mock

import pendulum

from app.data_warehouse import models
from app.exports.models import ExportTransactionStatus
from app.feeds import FeedType


class MockFullExportTransaction:
    id = 1
    created_at = pendulum.datetime(2022, 5, 19, 13, 27, 34)
    transaction_id = 125
    feed_type = FeedType.AUTH
    provider_slug = "test-slug"
    transaction_date = pendulum.datetime(2022, 5, 18, 10, 7, 00)
    spend_amount = 1500
    spend_currency = "GBP"
    loyalty_id = "876543"
    mid = "1234567"
    location_id = 9999
    merchant_internal_id = 10
    user_id = 10
    scheme_account_id = 2
    payment_card_account_id = 11
    credentials = {"card_number": "loyalty-123", "merchant_identifier": "876543"}
    status = ExportTransactionStatus.EXPORTED
    settlement_key = "ghy54rth4rty43r"
    auth_code = "123"
    approval_code = "123"


class MockPartExportTransaction:
    id = 1
    created_at = pendulum.datetime(2022, 5, 19, 13, 27, 34)
    transaction_id = 345
    feed_type = None
    provider_slug = "test-slug"
    transaction_date = pendulum.datetime(2022, 5, 18, 10, 7, 00)
    spend_amount = 1500
    spend_currency = "GBP"
    loyalty_id = "876543"
    mid = "1234567"
    location_id = None
    merchant_internal_id = None
    user_id = 10
    scheme_account_id = 2
    payment_card_account_id = None
    credentials = {"card_number": "loyalty-123", "merchant_identifier": "876543"}
    status = ExportTransactionStatus.EXPORTED
    settlement_key = None
    auth_code = "123"
    approval_code = "123"


@mock.patch("app.data_warehouse.queue.add", autospec=True)
def test_queue_data_warehouse_full_message(mocked_queue):
    # full message  means all the fields have values and are not None or empty
    models.send_unexported_transaction([MockFullExportTransaction()])

    mocked_queue.assert_called()
    assert mocked_queue.call_args[0][0]["transaction_id"] == 125
    assert mocked_queue.call_args[0][0]["merchant_internal_id"] == 10


@mock.patch("app.data_warehouse.queue.add", autospec=True)
def test_queue_data_warehouse_part_message(mocked_queue):
    # part message  means not all the fields have values some could be None or empty
    models.send_unexported_transaction([MockPartExportTransaction()])

    mocked_queue.assert_called()
    assert mocked_queue.call_args[0][0]["transaction_id"] == 345
    assert mocked_queue.call_args[0][0]["feed_type"] is None
    assert mocked_queue.call_args[0][0]["merchant_internal_id"] is None
