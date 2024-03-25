import datetime
import json
from unittest import mock

import pendulum
import pytest
import requests
import responses
import time_machine
from requests import RequestException

import settings
from app import db, models
from app.exports.agents.bases.singular_export_agent import FailedExport
from app.exports.agents.stonegate import InitialExportDelayRetry, Stonegate
from app.service.acteol import InternalError
from tests.fixtures import Default, get_or_create_export_transaction, get_or_create_pending_export

settings.DEBUG = False


MERCHANT_SLUG = "stonegate"
MIDS = Default.primary_mids

MOCK_URL = "http://stonegate.test"


REQUEST = {
    "AccountID": "account_id_123",
    "MemberNumber": "loyalty-123",
    "TransactionID": "db0b14a3-0ca8-4281-9a77-57b5b88ec0a4",
}
RESPONSE_SUCCESS = {"body": "", "status_code": 204, "timestamp": "2022-04-26 18:00:00"}
RESPONSE_ERROR = {"Error": None, "Message": "Origin ID not found"}


@pytest.fixture
def stonegate() -> Stonegate:
    return Stonegate()


@pytest.fixture
def export_transaction(db_session: db.Session) -> models.ExportTransaction:
    exp = get_or_create_export_transaction(
        session=db_session,
        provider_slug=MERCHANT_SLUG,
        mid=MIDS,
        primary_identifier=MIDS,
    )
    setattr(exp, "extra_fields", {"account_id": "account_id_123"})
    return exp


@pytest.fixture
def pending_export(export_transaction: models.ExportTransaction, db_session: db.Session) -> models.PendingExport:
    return get_or_create_pending_export(
        session=db_session, export_transaction=export_transaction, provider_slug=export_transaction.provider_slug
    )


def make_response(response_body: dict) -> requests.Response:
    response = requests.Response()
    response._content = json.dumps(response_body).encode("utf-8")
    return response


@pytest.fixture
def response() -> requests.Response:
    response_body = RESPONSE_ERROR
    return make_response(response_body)


def test_get_retry_datetime_with_exception(stonegate: Stonegate, response: requests.Response) -> None:
    result = stonegate.get_retry_datetime(retry_count=0, exception=RequestException(response=response))

    assert result is None


@time_machine.travel(pendulum.datetime(2022, 11, 24, 11, 0, 0, 0, "Europe/London"))
def test_get_retry_datetime_with_retry_count_zero(stonegate: Stonegate) -> None:
    result = stonegate.get_retry_datetime(retry_count=0)
    assert result == pendulum.datetime(2022, 11, 24, 11, 0, 0, 0, "Europe/London") + pendulum.duration(minutes=20)


@time_machine.travel(pendulum.datetime(2022, 11, 24, 11, 0, 0, 0, "Europe/London"))
def test_get_retry_datetime_with_retry_count_one(stonegate: Stonegate) -> None:
    result = stonegate.get_retry_datetime(retry_count=1)
    assert result == pendulum.datetime(2022, 11, 24, 11, 20, 0, 0, "Europe/London")


def test_get_retry_datetime_with_retry_count_greater_than_max(
    stonegate: Stonegate, response: requests.Response
) -> None:
    result = stonegate.get_retry_datetime(retry_count=40)
    assert result is None


@time_machine.travel(pendulum.datetime(2022, 11, 24, 11, 0, 0, 0, "Europe/London"))
def test_next_available_retry_time_run_time_is_past(stonegate: Stonegate) -> None:
    next_available_retry_time = stonegate.next_available_retry_time(10)

    assert next_available_retry_time == pendulum.datetime(2022, 11, 25, 10, 0, 0, 0, "Europe/London")


@time_machine.travel(pendulum.datetime(2022, 11, 24, 9, 0, 0, 0, "Europe/London"))
def test_next_available_retry_time_run_time_is_future(stonegate: Stonegate) -> None:
    next_available_retry_time = stonegate.next_available_retry_time(10)
    assert next_available_retry_time == pendulum.datetime(2022, 11, 24, 10, 0, 0, 0, "Europe/London")


def test_get_loyalty_identifier(stonegate: Stonegate, export_transaction: models.ExportTransaction) -> None:
    loyalty_identifier = stonegate.get_loyalty_identifier(export_transaction)
    assert loyalty_identifier == "loyalty-123"


def test_make_export_data(
    stonegate: Stonegate, export_transaction: models.ExportTransaction, db_session: db.Session
) -> None:
    export_data = stonegate.make_export_data(export_transaction, session=db_session)

    assert export_data.outputs[0].data == {
        "AccountID": "account_id_123",
        "MemberNumber": "loyalty-123",
        "TransactionID": "db0b14a3-0ca8-4281-9a77-57b5b88ec0a4",
    }
    assert export_data.transactions[0] == export_transaction
    assert export_data.extra_data == {
        "credentials": {
            "card_number": "loyalty-123",
            "merchant_identifier": "test_loyalty_id",
            "email": "test-123@testbink.com",
        }
    }


@responses.activate
@time_machine.travel(pendulum.datetime(2022, 11, 24, 11, 0, 0, 0, "Europe/London"))
@mock.patch("app.exports.agents.stonegate.atlas.make_audit_transactions")
@mock.patch("app.exports.agents.stonegate.atlas.make_audit_message")
@mock.patch("app.exports.agents.bases.singular_export_agent.atlas.queue_audit_message")
def test_export(
    queue_audit_message: mock.Mock,
    make_audit_message: mock.Mock,
    make_audit_transactions: mock.Mock,
    stonegate: Stonegate,
    pending_export: models.PendingExport,
    db_session: db.Session,
) -> None:
    responses.add(
        responses.POST,
        url="http://localhost/PostMatchedTransaction",
        json=RESPONSE_SUCCESS,
        status=204,
    )

    stonegate.handle_pending_export(pending_export, session=db_session)

    # Post to Wasabi
    assert responses.calls[0].request.url == "http://localhost/PostMatchedTransaction"
    responses.assert_call_count("http://localhost/PostMatchedTransaction", 1)
    assert json.loads(responses.calls[0].request.body) == REQUEST
    assert responses.calls[0].response.json() == RESPONSE_SUCCESS

    # Post to Atlas
    assert make_audit_transactions.call_args.args[0] == [pending_export.export_transaction]
    assert make_audit_message.call_args.args == (MERCHANT_SLUG, make_audit_transactions())
    assert make_audit_message.call_args.kwargs["request"] == REQUEST
    assert json.loads(make_audit_message.call_args.kwargs["response"]._content) == RESPONSE_SUCCESS
    assert make_audit_message.call_args.kwargs["request_url"] == "http://localhost/PostMatchedTransaction"
    assert queue_audit_message.call_count == 1


@responses.activate
@time_machine.travel(pendulum.datetime(2022, 11, 24, 9, 0, 0, 0, "Europe/London"))
@mock.patch("app.exports.agents.stonegate.atlas")
def test_export_before_10_30(
    mock_atlas, stonegate: Stonegate, export_transaction: models.ExportTransaction, db_session: db.Session
) -> None:
    responses.add(
        responses.POST,
        url="http://localhost/PostMatchedTransaction",
        json=RESPONSE_SUCCESS,
        status=204,
    )
    export_data = stonegate.make_export_data(export_transaction, session=db_session)
    with pytest.raises(InitialExportDelayRetry):
        stonegate.export(export_data, session=db_session)


@responses.activate
@time_machine.travel(pendulum.datetime(2022, 11, 24, 11, 0, 0, 0, "Europe/London"))
@mock.patch("app.exports.agents.stonegate.atlas")
def test_export_origin_id_not_found(
    mock_atlas, stonegate: Stonegate, export_transaction: models.ExportTransaction, db_session: db.Session
) -> None:
    responses.add(
        responses.POST,
        url="http://localhost/PostMatchedTransaction",
        json=RESPONSE_ERROR,
        status=204,
    )
    export_data = stonegate.make_export_data(export_transaction, session=db_session)

    result = stonegate.export(export_data, session=db_session)
    assert isinstance(result, FailedExport)
    assert result.reason == "origin id not found"


@responses.activate
@time_machine.travel(pendulum.datetime(2022, 11, 24, 11, 0, 0, 0, "Europe/London"))
@mock.patch("app.exports.agents.stonegate.atlas")
def test_export_receipt_no_not_found(
    mock_atlas, stonegate: Stonegate, export_transaction: models.ExportTransaction, db_session: db.Session
) -> None:
    response_body = {"Error": None, "Message": "Transaction with AccountID xxxxxx was not found"}
    responses.add(
        responses.POST,
        url="http://localhost/PostMatchedTransaction",
        json=response_body,
        status=204,
    )
    export_data = stonegate.make_export_data(export_transaction, session=db_session)
    result = stonegate.export(export_data, session=db_session)

    assert isinstance(result, FailedExport)
    assert result.reason == "transaction with accountid xxxxxx was not found"


@responses.activate
@time_machine.travel(pendulum.datetime(2022, 11, 24, 11, 0, 0, 0, "Europe/London"))
@mock.patch("app.exports.agents.stonegate.atlas")
def test_export_member_number_not_found(
    mock_atlas, stonegate: Stonegate, export_transaction: models.ExportTransaction, db_session: db.Session
) -> None:
    response_body = {"Error": None, "Message": "Member Number: xxxxxx was not found"}
    responses.add(
        responses.POST,
        url="http://localhost/PostMatchedTransaction",
        json=response_body,
        status=204,
    )
    export_data = stonegate.make_export_data(export_transaction, session=db_session)
    result = stonegate.export(export_data, session=db_session)
    assert isinstance(result, FailedExport)
    assert result.reason == "member number: xxxxxx was not found"


@responses.activate
@time_machine.travel(pendulum.datetime(2022, 11, 24, 11, 0, 0, 0, "Europe/London"))
@mock.patch("app.exports.agents.stonegate.atlas")
def test_export_points_not_awarded(
    mock_atlas, stonegate: Stonegate, export_transaction: models.ExportTransaction, db_session: db.Session
) -> None:
    response_body = {"Error": None, "Message": "Points are not added successfully"}
    responses.add(
        responses.POST,
        url="http://localhost/PostMatchedTransaction",
        json=response_body,
        status=204,
    )
    export_data = stonegate.make_export_data(export_transaction, session=db_session)
    result = stonegate.export(export_data, session=db_session)
    assert isinstance(result, FailedExport)
    assert result.reason == "points are not added successfully"


def test_get_response_result(stonegate: Stonegate, response: requests.Response) -> None:
    result = stonegate.get_response_result(response)

    assert result == "origin id not found"


@responses.activate
@time_machine.travel(pendulum.datetime(2022, 11, 24, 11, 0, 0, 0, "Europe/London"))
@mock.patch("app.exports.agents.stonegate.atlas")
def test_export_internal_error(
    mock_atlas, stonegate: Stonegate, export_transaction: models.ExportTransaction, db_session: db.Session
) -> None:
    response_body = {"Error": "Internal Error", "Message": None}
    responses.add(
        responses.POST,
        url="http://localhost/PostMatchedTransaction",
        json=response_body,
        status=204,
    )
    export_data = stonegate.make_export_data(export_transaction, session=db_session)
    with pytest.raises(InternalError):
        stonegate.export(export_data, session=db_session)


@responses.activate
@time_machine.travel(pendulum.datetime(2022, 11, 24, 11, 0, 0, 0, "Europe/London"))
@mock.patch("app.exports.agents.stonegate.atlas")
def test_stonegate_internal_errors_are_retried(
    mock_atlas, stonegate: Stonegate, export_transaction: models.ExportTransaction, db_session: db.Session
) -> None:
    response_body = {"Error": "Internal Error", "Message": None}
    responses.add(
        responses.POST,
        url="http://localhost/PostMatchedTransaction",
        json=response_body,
        status=204,
    )
    pending_export_transaction = get_or_create_pending_export(
        session=db_session, export_transaction=export_transaction, provider_slug=MERCHANT_SLUG
    )
    stonegate.handle_pending_export(pending_export_transaction, session=db_session)
    assert pending_export_transaction.retry_count == 0
    assert isinstance(pending_export_transaction.retry_at, datetime.datetime)
