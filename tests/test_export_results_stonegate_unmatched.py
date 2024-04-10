from unittest import mock

import pendulum
import pytest

import settings
from app.export_result.agents.stonegate import Stonegate

settings.VAULT_URL = "https://vault"
settings.DEBUG = False


MERCHANT_SLUG = "stonegate-unmatched"


@pytest.fixture
def stonegate() -> Stonegate:
    return Stonegate()


TRANSACTION_FILE_RESULT = (
    b"transaction_id,member_number,retailer_location_id,transaction_amount,transaction_date,uid,result\r\n"
    b"db0b14a3-0ca8-4281-9a77-57b5b88ec0a4,test_loyalty_id,1234,5566,2024-03-25 16:54:33,test-uid-1234,rewarded\r\n"
)

TRANSACTION_DATA = {
    "transaction_id": "db0b14a3-0ca8-4281-9a77-57b5b88ec0a4",
    "member_number": "test_loyalty_id",
    "retailer_location_id": "1234",
    "transaction_amount": 5566,
    "transaction_date": pendulum.parse("2024-03-25 16:54:33").isoformat(),
    "uid": "test-uid-1234",
    "result": "rewarded",
}

AUDIT_DATA = [
    {
        "event_date_time": mock.ANY,
        "event_type": "transaction.exported.response",
        "transaction_id": "db0b14a3-0ca8-4281-9a77-57b5b88ec0a4",
        "user_id": "",
        "spend_amount": 5566,
        "transaction_date": pendulum.parse("2024-03-25 16:54:33").isoformat(),
        "loyalty_identifier": "test_loyalty_id",
        "retailer_location_id": "1234",
        "record_uid": "",
        "provider_slug": MERCHANT_SLUG,
        "export_uid": "test-uid-1234",
        "result": "rewarded",
    }
]


def test_yield_results_data():
    generator = Stonegate().yield_results_data(TRANSACTION_FILE_RESULT)
    assert next(generator) == TRANSACTION_DATA


def test_format_audit_transaction():
    audit_data = Stonegate().format_audit_transaction(TRANSACTION_DATA)
    assert TRANSACTION_DATA["transaction_id"] == audit_data[0]["transaction_id"]
    assert TRANSACTION_DATA["transaction_amount"] == audit_data[0]["spend_amount"]
