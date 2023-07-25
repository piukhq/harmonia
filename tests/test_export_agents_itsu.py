from unittest import mock

import pendulum
import pytest

from app import db, models
from app.exports.agents import AgentExportData, AgentExportDataOutput
from app.exports.agents.itsu import Itsu
from app.feeds import FeedType
from tests.fixtures import Default, get_or_create_export_transaction, get_or_create_transaction

TRANSACTION_ID = "1234567"
PRIMARY_MIDS = Default.primary_mids
SECONDARY_MID = Default.secondary_mid
TRANSACTION_DATE = pendulum.DateTime(2022, 11, 1, 17, 14, 8, 838138, tzinfo=pendulum.timezone("Europe/London"))
SETTLEMENT_KEY = "123456"
LOYALTY_ID = "10"
MERCHANT_SLUG = "itsu"

REQUEST_BODY = {
    "OrderID": "123",
    "SubTransactions": [
        {
            "CustomerDetails": {
                "MemberNumber": "loyalty-123",
                "ExternalIdentifier": {"ExternalID": "", "ExternalSource": ""},
            },
            "TotalAmount": 5566,
            "PaidAmount": 5566,
            "OrderStatusID": 1,
            "OrderTypeID": 1,
            "OrderChannelID": 1,
            "OrderItems": [{"ItemID": "1", "ItemName": "Bink Transaction", "ItemPrice": 5566}],
        }
    ],
    "OrderDate": pendulum.instance(TRANSACTION_DATE).in_timezone("Europe/London").format("YYYY-MM-DDTHH:mm:ss"),
    "Location": {"ActeolSiteID": None},
    "Source": "BINK",
}
RESPONSE_BODY = {"ResponseStatus": True, "Errors": []}


@pytest.fixture
def transaction(db_session: db.Session) -> None:
    get_or_create_transaction(
        session=db_session,
        transaction_id=TRANSACTION_ID,
        merchant_identifier_ids=[1],
        mids=PRIMARY_MIDS,
        merchant_slug=MERCHANT_SLUG,
        settlement_key=SETTLEMENT_KEY,
        card_token="9876543",
        first_six="666666",
        last_four="4444",
        auth_code="666655",
    )


@pytest.fixture
def export_transaction() -> models.ExportTransaction:
    return get_or_create_export_transaction(
        transaction_id=TRANSACTION_ID,
        provider_slug=MERCHANT_SLUG,
        transaction_date=pendulum.instance(TRANSACTION_DATE),
        loyalty_id=LOYALTY_ID,
        mid=SECONDARY_MID,
        primary_identifier=PRIMARY_MIDS[0],
        feed_type=FeedType.AUTH,
        settlement_key=SETTLEMENT_KEY,
        payment_card_account_id=1,
    )


@mock.patch("app.exports.agents.itsu.uuid.uuid4", return_value="123")
def test_make_export_data(mock_uuid, export_transaction: models.ExportTransaction, db_session: db.Session) -> None:
    itsu = Itsu()

    expected_result = AgentExportData(
        outputs=[
            AgentExportDataOutput(
                key="export.json",
                data=REQUEST_BODY,
            )
        ],
        transactions=[export_transaction],
        extra_data={
            "credentials": {
                "card_number": "loyalty-123",
                "email": "test-123@testbink.com",
                "merchant_identifier": "test_loyalty_id",
            }
        },
    )
    result = itsu.make_export_data(export_transaction, db_session)

    assert expected_result == result


@mock.patch("app.exports.agents.itsu.uuid.uuid4", return_value="123")
@mock.patch("app.exports.agents.itsu.atlas")
@mock.patch("app.service.itsu.ItsuApi.post", return_value=RESPONSE_BODY)
def test_export(
    mock_itsu_post, mock_atlas, mock_uuid, export_transaction: models.ExportTransaction, db_session: db.Session
) -> None:
    itsu = Itsu()
    export_data = itsu.make_export_data(export_transaction, db_session)

    itsu.export(export_data, session=db_session)

    # Post to Itsu
    mock_itsu_post.assert_called_once_with("api/Transaction/PostOrder", REQUEST_BODY, name="post_matched_transaction")

    # Post to Atlas
    assert mock_atlas.make_audit_transactions.call_args.args[0] == [export_transaction]
    assert mock_atlas.make_audit_message.call_args.args == (MERCHANT_SLUG, mock_atlas.make_audit_transactions())
    assert mock_atlas.make_audit_message.call_args.kwargs == {
        "request": REQUEST_BODY,
        "request_timestamp": mock.ANY,
        "response": RESPONSE_BODY,
        "response_timestamp": mock.ANY,
        "request_url": "http://localhost/api/Transaction/PostOrder",
        "retry_count": 0,
    }
    assert mock_atlas.queue_audit_message.call_count == 1
