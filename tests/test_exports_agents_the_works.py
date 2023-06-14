from unittest import mock
from unittest.mock import ANY

import pendulum
import pytest
from sqlalchemy.exc import NoResultFound

from app import db, models
from app.currency import to_pounds
from app.exports.agents import AgentExportData, AgentExportDataOutput
from app.exports.agents.the_works import TheWorks
from app.reporting import sanitise_logs
from tests.fixtures import (
    Default,
    get_or_create_export_transaction,
    get_or_create_pending_export,
    get_or_create_transaction,
)

TRANSACTION_ID = "1234567"
PRIMARY_IDENTIFIER = Default.primary_mids[0]
SECONDARY_IDENTIFIER = Default.secondary_mid
TRANSACTION_DATE = pendulum.DateTime(2022, 11, 1, 17, 14, 8, 838138, tzinfo=pendulum.timezone("Europe/London"))
SETTLEMENT_KEY = "123456"
LOYALTY_ID = "10"
MERCHANT_SLUG = "the-works"

REQUEST_BODY_911 = {
    "jsonrpc": "2.0",
    "method": "dc_911",  # request method
    "id": 1,
    "params": [
        "en",  # language code
        ANY,
        "username1",
        "password1",
        ANY,  # givex number
        to_pounds(Default.spend_amount),
    ],
}

RESPONSE_BODY_911 = {
    "body": "Bink Transaction details processed successfully!",
    "status_code": 200,
    "timestamp": "2023-05-16 16:36:45",
}

HISTORY_TRANSACTIONS = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": [
        "0001111122233333",
        "0",
        "0.50",
        "GBP",
        "0",
        [
            [
                "2023-05-04",
                "12:39:49",
                "Redeem",
                "-50.0",
                "Blackpool",
                "",
                [],
                "920045948",
                "0",
                "2023-05-04 12:39:49",
                "2023-05-04 12:39:49",
                "R",
                "0",
                "102 - Blackpool - POS",
                "0",
                "-50",
                "0",
                "0",
                "6096",
            ],
            [
                "2023-05-04",
                "10:57:14",
                "Reduction",
                "-25.0",
                "Blackpool",
                "",
                [],
                "931740868",
                "32",
                "2023-05-04 10:57:14",
                "2023-05-04 10:57:14",
                "E",
                "0",
                "Bink UAT – The Works",
                "0",
                "-25",
                "0",
                "0",
                "6096",
            ],
            [
                "2023-05-04",
                "10:54:48",
                "Increment",
                "275.0",
                "Blackpool",
                "",
                [],
                "931740867",
                "32",
                "2023-05-04 10:54:48",
                "2023-05-04 10:54:48",
                "I",
                "0",
                "Bink UAT – The Works",
                "0",
                "25",
                "0",
                "0",
                "6096",
            ],
            [
                "2023-05-04",
                "10:47:38",
                "Increment",
                "50.0",
                "Blackpool",
                "",
                [],
                "931740863",
                "32",
                "2023-05-04 10:47:38",
                "2023-05-04 10:47:38",
                "I",
                "0",
                "Bink UAT – The Works",
                "0",
                "50",
                "0",
                "0",
                "6096",
            ],
        ],
        "4",
        "633884-100000726",
        "None",
        "",
    ],
}

FAILED_HISTORY = {"jsonrpc": "2.0", "id": 1, "result": ["123348509238469083", "2", "Cert not exist"]}


@pytest.fixture
def transaction(db_session: db.Session) -> None:
    get_or_create_transaction(
        session=db_session,
        transaction_id=TRANSACTION_ID,
        transaction_date="2023-05-04T11:06:23",
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
        transaction_date="2023-05-04T11:06:23",
    )


@pytest.fixture
def pending_export(export_transaction: models.ExportTransaction, db_session: db.Session) -> models.PendingExport:
    return get_or_create_pending_export(
        session=db_session, export_transaction=export_transaction, provider_slug=MERCHANT_SLUG
    )


@mock.patch("app.service.the_works.TheWorksAPI._history_request")
@mock.patch("app.service.the_works.TheWorksAPI.get_credentials")
def test_find_export_transaction_already_rewarded(
    mock_get_credentials, mock_history_request, pending_export: models.PendingExport, db_session: db.Session
) -> None:
    mock_get_credentials.return_value = ("username1", "password1")
    mock_history_request.return_value = HISTORY_TRANSACTIONS
    export_transaction.settlement_key = None
    the_works = TheWorks()
    with pytest.raises(NoResultFound):
        the_works.find_export_transaction(pending_export, session=db_session)


@mock.patch("app.service.the_works.TheWorksAPI._history_request")
@mock.patch("app.service.the_works.TheWorksAPI.get_credentials")
def test_find_export_transaction_to_be_rewarded(
    mock_get_credentials, mock_history_request, pending_export: models.PendingExport, db_session: db.Session
) -> None:
    mock_get_credentials.return_value = ("username1", "password1")
    mock_history_request.return_value = HISTORY_TRANSACTIONS
    pending_export.export_transaction.spend_amount = 1735
    the_works = TheWorks()

    to_be_rewarded = the_works.find_export_transaction(pending_export, session=db_session)
    assert to_be_rewarded == pending_export.export_transaction


@mock.patch("app.service.the_works.TheWorksAPI._history_request")
@mock.patch("app.service.the_works.TheWorksAPI.get_credentials")
def test_find_export_transaction_error_code(
    mock_get_credentials, mock_history_request, pending_export: models.PendingExport, db_session: db.Session
) -> None:
    mock_get_credentials.return_value = ("username1", "password1")
    mock_history_request.return_value = FAILED_HISTORY
    export_transaction.settlement_key = None
    the_works = TheWorks()
    with pytest.raises(NoResultFound):
        the_works.find_export_transaction(pending_export, session=db_session)


@mock.patch("app.service.the_works.TheWorksAPI.get_credentials")
def test_make_export_data(
    mock_get_credentials, export_transaction: models.ExportTransaction, db_session: db.Session
) -> None:
    mock_get_credentials.return_value = ("username1", "password1")
    the_works = TheWorks()

    expected_result = AgentExportData(
        outputs=[
            AgentExportDataOutput(
                key="export.json",
                data=REQUEST_BODY_911,
            )
        ],
        transactions=[export_transaction],
        extra_data=None,
    )
    result = the_works.make_export_data(export_transaction, db_session)

    # Improve this check by adding in more field checks. We can't compare the two instances directly because there
    # is a uuid generated for each transaction sent to givex for the transaction code field.
    assert result.transactions[0].loyalty_id == expected_result.transactions[0].loyalty_id


@mock.patch("app.service.the_works.TheWorksAPI.get_credentials")
@mock.patch("app.exports.agents.the_works.atlas")
@mock.patch("app.service.the_works.TheWorksAPI.transactions", return_value=RESPONSE_BODY_911)
def test_export(
    mock_the_works_post,
    mock_atlas,
    mock_get_credentials,
    export_transaction: models.ExportTransaction,
    db_session: db.Session,
) -> None:
    mock_get_credentials.return_value = ("username1", "password1")
    the_works = TheWorks()
    export_data = the_works.make_export_data(export_transaction, db_session)

    the_works.export(export_data, session=db_session)

    # Post to the_works
    mock_the_works_post.assert_called_once_with(REQUEST_BODY_911, "")

    # Post to Atlas
    assert mock_atlas.make_audit_transactions.call_args.args[0] == [export_transaction]
    assert mock_atlas.make_audit_message.call_args.args == (MERCHANT_SLUG, mock_atlas.make_audit_transactions())
    assert mock_atlas.make_audit_message.call_args.kwargs == {
        "request": sanitise_logs(REQUEST_BODY_911, "the-works"),
        "request_timestamp": mock.ANY,
        "response": RESPONSE_BODY_911,
        "response_timestamp": mock.ANY,
        "request_url": "https://reflector.staging.gb.bink.com/mock/",
        "retry_count": 0,
    }
    assert mock_atlas.queue_audit_message.call_count == 1
