from unittest import mock

import pendulum
import pytest
from requests.models import Response

from app import db, models
from app.exports.agents import AgentExportData, AgentExportDataOutput
from app.exports.agents.tgi_fridays import ExportDelayRetry, TGIFridays
from app.reporting import sanitise_logs
from tests.fixtures import (
    Default,
    get_or_create_export_transaction,
    get_or_create_pending_export,
    get_or_create_transaction,
)

KEY_PREFIX = "txmatch:config:exports.agents.tgi-fridays"
TRANSACTION_ID = "1234567"
PRIMARY_IDENTIFIER = Default.primary_mids[0]
SECONDARY_IDENTIFIER = Default.secondary_mid
TRANSACTION_DATE = pendulum.DateTime(2024, 2, 20, 17, 14, 8, 838138, tzinfo=pendulum.timezone("Europe/London"))
SETTLEMENT_KEY = "123456"
LOYALTY_ID = "11"
MERCHANT_SLUG = "tgi-fridays"

REQUEST = {
    "user_id": "test_loyalty_id",
    "message": "You’ve been awarded stripes",
    "gift_count": 51,
    "location_id": "test_location_id",
}

export_resp = mock.Mock(spec=Response)
export_resp.status_code = 201
export_resp.url = "https://test.tgi.com/path/transaction"
export_resp.json.return_value = {}

RESPONSE_ERROR = {"Error": None, "Message": "Origin ID not found"}

# This is not the whole response from Punchh, only the "checkins" section of the response.
HISTORY_TRANSACTIONS = [
    {
        "checkin_type": None,
        "channel": None,
        "receipt_amount": None,
        "receipt_number": None,
        "receipt_date": None,
        "ip_address": None,
        "bar_code": None,
        "created_at": "2019-12-06T14:01:15Z",
        "location_name": "ADDRESS_GOES_HERE",
    },
    {
        "checkin_type": "PosCheckin",
        "channel": "POS",
        "receipt_amount": 50.60,
        "receipt_number": "8204",
        "receipt_date": "2024-02-20T11:06:23Z",
        "ip_address": "IP_ADDRESS_GOES_HERE",
        "bar_code": "BARCODE_GOES_HERE",
        "created_at": "2024-02-20T11:06:23Z",
        "location_name": "ADDRESS_GOES_HERE",
    },
]

history_response = mock.Mock(spec=Response)
history_response.json.return_value = HISTORY_TRANSACTIONS
history_response.status_code = 200
history_response.url = "http://testing.punchh.com"

FAILED_HISTORY = {"errors": {"user_not_found": "Cannot find corresponding user with ID: 62779001"}}
failed_history_response = mock.Mock(spec=Response)
failed_history_response.json.return_value = FAILED_HISTORY
failed_history_response.status_code = 404
failed_history_response.url = "http://testing.punchh.com"


@pytest.fixture
def transaction(db_session: db.Session) -> None:
    get_or_create_transaction(
        session=db_session,
        transaction_id=TRANSACTION_ID,
        transaction_date="2024-02-20T11:06:23",
        merchant_identifier_ids=[1],
        primary_identifier=PRIMARY_IDENTIFIER,
        merchant_slug=MERCHANT_SLUG,
        settlement_key=SETTLEMENT_KEY,
        card_token="9876543",
        first_six="666666",
        last_four="4444",
        auth_code="666655",
    )


@pytest.fixture
def export_transaction(db_session: db.Session) -> models.ExportTransaction:
    return get_or_create_export_transaction(
        session=db_session,
        provider_slug=MERCHANT_SLUG,
        mid=PRIMARY_IDENTIFIER,
        primary_identifier=PRIMARY_IDENTIFIER,
        transaction_date="2024-02-20T11:06:23",
        location_id="test_location_id",
        extra_fields={"amount": 50.60},
    )


@pytest.fixture
def pending_export(export_transaction: models.ExportTransaction, db_session: db.Session) -> models.PendingExport:
    return get_or_create_pending_export(
        session=db_session, export_transaction=export_transaction, provider_slug=MERCHANT_SLUG
    )


@mock.patch("app.service.tgi_fridays.TGIFridaysAPI.transaction_history")
def test_should_send_export_first_attempt_delay(
    mock_transaction_history,
    export_transaction: models.ExportTransaction,
    db_session: db.Session,
) -> None:
    mock_transaction_history.return_value = HISTORY_TRANSACTIONS
    tgi_fridays = TGIFridays()
    # the first attempt should raise a delay exception
    with pytest.raises(ExportDelayRetry):
        tgi_fridays.should_send_export(export_transaction, 0, session=db_session)


@mock.patch("app.service.tgi_fridays.TGIFridaysAPI.transaction_history")
def test_should_send_export_false_already_rewarded(
    mock_transaction_history,
    export_transaction: models.ExportTransaction,
    db_session: db.Session,
) -> None:
    mock_transaction_history.return_value = HISTORY_TRANSACTIONS
    tgi_fridays = TGIFridays()
    should_export = tgi_fridays.should_send_export(export_transaction, 1, session=db_session)
    assert not should_export


@mock.patch("app.service.tgi_fridays.TGIFridaysAPI.transaction_history")
def test_should_send_export_true_to_be_rewarded(
    mock_transaction_history,
    export_transaction: models.ExportTransaction,
    db_session: db.Session,
) -> None:
    mock_transaction_history.return_value = HISTORY_TRANSACTIONS
    export_transaction.extra_fields["amount"] = 17.35
    tgi_fridays = TGIFridays()

    to_be_rewarded = tgi_fridays.should_send_export(export_transaction, 1, session=db_session)
    assert to_be_rewarded


@mock.patch("app.service.tgi_fridays.TGIFridaysAPI.transaction_history")
def test_should_send_export_error_code(
    mock_transaction_history, export_transaction: models.ExportTransaction, db_session: db.Session
) -> None:
    mock_transaction_history.return_value = failed_history_response
    tgi_fridays = TGIFridays()
    with pytest.raises(Exception):
        tgi_fridays.should_send_export(export_transaction, session=db_session)


def test_make_export_data(export_transaction: models.ExportTransaction, db_session: db.Session) -> None:
    tgi_fridays = TGIFridays()

    expected_result = AgentExportData(
        outputs=[
            AgentExportDataOutput(
                key="export.json",
                data=REQUEST,
            )
        ],
        transactions=[export_transaction],
        extra_data=None,
    )
    result = tgi_fridays.make_export_data(export_transaction, db_session)

    assert result.transactions[0].loyalty_id == expected_result.transactions[0].loyalty_id


@mock.patch("app.exports.agents.tgi_fridays.atlas")
@mock.patch("app.service.tgi_fridays.TGIFridaysAPI.transactions", return_value=export_resp)
def test_export(
    mock_tgi_fridays_post,
    mock_atlas,
    export_transaction: models.ExportTransaction,
    db_session: db.Session,
) -> None:
    tgi_fridays = TGIFridays()
    export_data = tgi_fridays.make_export_data(export_transaction, db_session)

    tgi_fridays.export(export_data, retry_count=1, session=db_session)

    # Post to tgi_fridays
    mock_tgi_fridays_post.assert_called_once_with(REQUEST)

    # Post to Atlas
    assert mock_atlas.make_audit_transactions.call_args.args[0] == [export_transaction]
    assert mock_atlas.make_audit_message.call_args.args == (MERCHANT_SLUG, mock_atlas.make_audit_transactions())
    assert mock_atlas.make_audit_message.call_args.kwargs == {
        "request": sanitise_logs(REQUEST, "tgi-fridays"),
        "request_timestamp": mock.ANY,
        "response": export_resp,
        "response_timestamp": mock.ANY,
        "request_url": "https://test.tgi.com/path/transaction",
        "retry_count": 1,
    }
    assert mock_atlas.queue_audit_message.call_count == 1
