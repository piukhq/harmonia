from unittest import mock

import pendulum
import pytest
import responses

from app import db, encryption, models
from app.exports.agents import AgentExportData, AgentExportDataOutput
from app.exports.agents.slim_chickens import SlimChickens
from app.feeds import FeedType
from tests.fixtures import (
    Default,
    get_or_create_export_transaction,
    get_or_create_pending_export,
    get_or_create_transaction,
)

TRANSACTION_ID = "1234567"
PRIMARY_MIDS = Default.primary_mids
SECONDARY_MID = Default.secondary_mid
TRANSACTION_DATE = pendulum.DateTime(2022, 11, 1, 17, 14, 8, 838138, tzinfo=pendulum.timezone("Europe/London"))
SETTLEMENT_KEY = "123456"
LOYALTY_ID = "10"
MERCHANT_SLUG = "slim-chickens"

SECRETS = {"channel_key": "test", "client_secret": "test-secret", "client_id": "test-client-id"}

WALLET_DATA = {
    "wallet": [
        {
            "itemId": "2b9811f91c4545b7877e78f663b9bb9b",
            "voucherCode": "123456",
            "voucherExpiry": "2024-06-22T22:59:59Z",
        },
        {
            "itemId": "2b9811f91c4545b7877e78f663b9bb9b",
            "voucherCode": "dfsdfsdf",
            "voucherExpiry": "2024-06-22T22:59:59Z",
        },
        {
            "itemId": "2b9811f91c4545b7877e78f663b9bb9b",
            "voucherCode": "inprogress_voucher",
            "voucherExpiry": "2024-06-22T22:59:59Z",
            "cardPoints": "0",
        },
        {
            "itemId": "2b9811f91c4545b7877e78f663b9bb9b",
            "voucherCode": "323123121",
            "voucherExpiry": "2024-06-22T22:59:59Z",
        },
    ]
}

REQUEST_BODY = {
    "token": "token-123",
    "location": {
        "incomingIdentifier": None,
        "parentIncomingIdentifier": "slimchickens",
    },
}
RESPONSE_BODY = {
    "body": "Bink Transaction details processed sucessfully!",
    "status_code": 200,
    "timestamp": "2022-11-02 16:36:45",
}


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
        transaction_date=TRANSACTION_DATE,
        loyalty_id=LOYALTY_ID,
        mid=SECONDARY_MID,
        primary_identifier=PRIMARY_MIDS[0],
        feed_type=FeedType.AUTH,
        payment_card_account_id=1,
        credentials=encryption.encrypt_credentials(
            {
                "password": "passpass",
                "email": "email@test.com",
            }
        ),
    )


@pytest.fixture
def pending_export(export_transaction: models.ExportTransaction, db_session: db.Session) -> models.PendingExport:
    export_transaction.id = TRANSACTION_ID
    export_transaction.spend_amount = 50
    return get_or_create_pending_export(
        session=db_session, export_transaction=export_transaction, provider_slug=MERCHANT_SLUG
    )


@responses.activate
@mock.patch("app.exports.agents.slim_chickens._read_secrets", return_value=SECRETS)
def test_get_transaction_token(
    mock_read_secrets, export_transaction: models.ExportTransaction, db_session: db.Session
) -> None:

    url = "https://localhost-auth/search"
    json = WALLET_DATA
    responses.add(responses.POST, url, json=json)

    slim_chickens = SlimChickens()
    auth_token = slim_chickens.get_transaction_token(export_transaction, session=db_session)
    assert slim_chickens.auth_header == "ZW1haWxAdGVzdC5jb20tdGVzdDpwYXNzcGFzcw=="
    assert auth_token == "inprogress_voucher"


@mock.patch("app.exports.agents.slim_chickens.SlimChickens.get_transaction_token", return_value="token-123")
@mock.patch("app.exports.agents.slim_chickens._read_secrets", return_value=SECRETS)
def test_make_export_data(
    mock_read_secrets, mock_auth_token, export_transaction: models.ExportTransaction, db_session: db.Session
) -> None:
    slim_chickens = SlimChickens()
    slim_chickens.spend_threshold = 0
    expected_result = AgentExportData(
        outputs=[
            AgentExportDataOutput(
                key="export.json",
                data=REQUEST_BODY,
            )
        ],
        transactions=[export_transaction],
        extra_data=None,
    )
    result = slim_chickens.make_export_data(export_transaction, db_session)

    assert result == expected_result


@mock.patch("app.exports.agents.slim_chickens.SlimChickens.get_transaction_token", return_value="token-123")
@mock.patch("app.exports.agents.slim_chickens._read_secrets", return_value=SECRETS)
@mock.patch("app.exports.agents.slim_chickens.atlas")
@mock.patch("app.service.slim_chickens.SlimChickensApi.post_matched_transaction", return_value=RESPONSE_BODY)
def test_export(
    mock_slim_chickens_post,
    mock_atlas,
    mock_read_secrets,
    mock_get_token,
    export_transaction: models.ExportTransaction,
    db_session: db.Session,
) -> None:
    slim_chickens = SlimChickens()
    slim_chickens.spend_threshold = 0
    slim_chickens.secrets = SECRETS
    slim_chickens.auth_header = {"Authorization": "Basic 123"}
    export_data = slim_chickens.make_export_data(export_transaction, db_session)

    slim_chickens.export(export_data, session=db_session)

    # Post to SlimChickens
    mock_slim_chickens_post.assert_called_once_with(REQUEST_BODY, "/2.0/connect/account/redeem")
    mock_get_token.assert_called_once_with(export_transaction, db_session)

    # Post to Atlas
    assert mock_atlas.make_audit_transactions.call_args.args[0] == [export_transaction]
    assert mock_atlas.make_audit_message.call_args.args == (MERCHANT_SLUG, mock_atlas.make_audit_transactions())
    assert mock_atlas.make_audit_message.call_args.kwargs == {
        "request": REQUEST_BODY,
        "request_timestamp": mock.ANY,
        "response": RESPONSE_BODY,
        "response_timestamp": mock.ANY,
        "request_url": "https://localhost/2.0/connect/account/redeem",
        "retry_count": 0,
    }
    assert mock_atlas.queue_audit_message.call_count == 1


@mock.patch("app.exports.agents.slim_chickens._read_secrets", return_value=SECRETS)
def test_find_export_transaction_below_threshold(
    mock_read_secrets,
    pending_export,
    db_session: db.Session,
) -> None:
    slim_chickens = SlimChickens()
    with pytest.raises(db.NoResultFound):
        slim_chickens.find_export_transaction(pending_export=pending_export, session=db_session)
