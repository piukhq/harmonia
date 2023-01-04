from unittest import mock

import pendulum
import pytest
import responses
import time_machine
from requests import RequestException
from sqlalchemy.exc import NoResultFound

from app import db, models
from app.exports.agents import AgentExportData, SingularExportAgent
from app.exports.exceptions import MissingExportData
from app.exports.models import ExportTransactionStatus
from tests.fixtures import Default, get_or_create_export_transaction, get_or_create_pending_export

TRANSACTION_ID = Default.transaction_id
TRANSACTION_DATE = Default.transaction_date
PRIMARY_IDENTIFIER = Default.primary_identifier
MERCHANT_SLUG = "mock-singular-export-agent"


class MockSingularExportAgent(SingularExportAgent):
    provider_slug = MERCHANT_SLUG

    def __init__(self):
        super().__init__()


@pytest.fixture
def mock_singular_export_agent() -> MockSingularExportAgent:
    return MockSingularExportAgent()


@pytest.fixture
def export_transaction(db_session: db.Session) -> models.ExportTransaction:
    return get_or_create_export_transaction(
        session=db_session,
        provider_slug=MERCHANT_SLUG,
    )


@pytest.fixture
def pending_export(export_transaction: models.ExportTransaction, db_session: db.Session) -> models.PendingExport:
    return get_or_create_pending_export(
        session=db_session, export_transaction=export_transaction, provider_slug=MERCHANT_SLUG
    )


def raise_missing_export_data_exception(export_transaction, session) -> None:
    raise MissingExportData("Something is missing")


def raise_exception(export_data, retry_count, session) -> None:
    raise Exception("Something went wrong")


def make_export_data(export_transaction, session) -> AgentExportData:
    return AgentExportData(
        outputs=[],
        transactions=[export_transaction],
        extra_data={},
    )


def drop_export_transaction(db_session: db.Session, export_transaction: models.ExportTransaction) -> None:
    drop_export_transaction_constraints = "ALTER TABLE export_transaction DISABLE TRIGGER ALL"
    db_session.execute(drop_export_transaction_constraints)
    db_session.delete(export_transaction)
    db_session.commit()


@time_machine.travel(pendulum.datetime(2022, 11, 24, 9, 0, 0, 0, "Europe/London"))
def test_simple_retry(mock_singular_export_agent: MockSingularExportAgent) -> None:
    simple_retry = mock_singular_export_agent.simple_retry(
        retry_count=3, delay=pendulum.duration(minutes=20), max_tries=4
    )

    assert simple_retry == pendulum.datetime(2022, 11, 24, 9, 20, 0, 0, "Europe/London")


@time_machine.travel(pendulum.datetime(2022, 11, 24, 9, 0, 0, 0, "Europe/London"))
def test_simple_retry_count_exceeds_max_retries(mock_singular_export_agent: MockSingularExportAgent) -> None:
    simple_retry = mock_singular_export_agent.simple_retry(
        retry_count=3, delay=pendulum.duration(minutes=20), max_tries=2
    )

    assert simple_retry is None


@time_machine.travel(pendulum.datetime(2022, 11, 24, 9, 0, 0, 0, "Europe/London"))
def test_get_retry_datetime(mock_singular_export_agent: MockSingularExportAgent) -> None:
    simple_retry = mock_singular_export_agent.get_retry_datetime(
        retry_count=3,
    )

    assert simple_retry == pendulum.datetime(2022, 11, 24, 9, 20, 0, 0, "Europe/London")


def test_run_not_implemented(mock_singular_export_agent: MockSingularExportAgent) -> None:
    with pytest.raises(NotImplementedError) as e:
        mock_singular_export_agent.run()

    assert (
        e.value.args[0]
        == "MockSingularExportAgent is a singular export agent and as such must be run via the export worker."
    )


def test_export_not_implemented(mock_singular_export_agent: MockSingularExportAgent, db_session: db.Session) -> None:
    with pytest.raises(NotImplementedError) as e:
        mock_singular_export_agent.export(
            AgentExportData(outputs={}, transactions={}, extra_data={}), session=db_session
        )

    assert (
        e.value.args[0]
        == "Override the export method in your agent to act as the entry point into the singular export process."
    )


def test_export_all_not_implemented(
    mock_singular_export_agent: MockSingularExportAgent, db_session: db.Session
) -> None:
    with pytest.raises(NotImplementedError) as e:
        mock_singular_export_agent.export_all(session=db_session)

    assert (
        e.value.args[0]
        == "MockSingularExportAgent is a singular export agent and as such does not support batch exports."
    )


def test_find_export_transaction(
    export_transaction: models.ExportTransaction,
    pending_export: models.PendingExport,
    mock_singular_export_agent: MockSingularExportAgent,
    db_session: db.Session,
) -> None:
    matched_transaction = mock_singular_export_agent.find_export_transaction(pending_export, session=db_session)

    assert matched_transaction == export_transaction


def test_find_export_transaction_no_match(
    export_transaction: models.ExportTransaction,
    pending_export: models.PendingExport,
    mock_singular_export_agent: MockSingularExportAgent,
    db_session: db.Session,
) -> None:
    drop_export_transaction(db_session, export_transaction)
    with pytest.raises(NoResultFound):
        mock_singular_export_agent.find_export_transaction(pending_export, session=db_session)


def test_handle_pending_export_no_export_transaction(
    export_transaction: models.ExportTransaction,
    pending_export: models.PendingExport,
    mock_singular_export_agent: MockSingularExportAgent,
    db_session: db.Session,
) -> None:
    drop_export_transaction(db_session, export_transaction)

    assert db_session.query(models.PendingExport).one() == pending_export

    mock_singular_export_agent.handle_pending_export(pending_export, session=db_session)

    assert db_session.query(models.PendingExport).one_or_none() is None


@mock.patch.object(SingularExportAgent, "make_export_data", side_effect=raise_missing_export_data_exception)
def test_handle_pending_export_missing_export_data(
    mock_make_export_data,
    export_transaction: models.ExportTransaction,
    pending_export: models.PendingExport,
    mock_singular_export_agent: MockSingularExportAgent,
    db_session: db.Session,
) -> None:
    assert db_session.query(models.PendingExport).one() == pending_export

    mock_singular_export_agent.handle_pending_export(pending_export, session=db_session)

    assert db_session.query(models.ExportTransaction).one().status == ExportTransactionStatus.EXPORT_FAILED
    assert db_session.query(models.PendingExport).one_or_none() is None


@mock.patch.object(SingularExportAgent, "_send_export_data", side_effect=raise_exception)
@mock.patch.object(SingularExportAgent, "make_export_data", side_effect=make_export_data)
@mock.patch.object(SingularExportAgent, "_retry_pending_export")
def test_handle_pending_export_exception_sending_export_data(
    mock_retry_pending_export,
    mock_make_export_data,
    mock_send_export_data,
    export_transaction: models.ExportTransaction,
    pending_export: models.PendingExport,
    mock_singular_export_agent: MockSingularExportAgent,
    db_session: db.Session,
) -> None:
    assert db_session.query(models.PendingExport).one() == pending_export

    mock_singular_export_agent.handle_pending_export(pending_export, session=db_session)

    assert db_session.query(models.PendingExport).one() == pending_export
    assert mock_retry_pending_export.call_args.args[0] == pending_export


@mock.patch.object(SingularExportAgent, "_send_export_data", side_effect=raise_exception)
@mock.patch.object(SingularExportAgent, "make_export_data", side_effect=make_export_data)
@mock.patch.object(SingularExportAgent, "get_retry_datetime", return_value=None)
def test_handle_pending_export_exception_sending_export_data_no_retry_at(
    mock_get_retry_datetime,
    mock_make_export_data,
    mock_send_export_data,
    export_transaction: models.ExportTransaction,
    pending_export: models.PendingExport,
    mock_singular_export_agent: MockSingularExportAgent,
    db_session: db.Session,
) -> None:
    assert db_session.query(models.PendingExport).one() == pending_export

    mock_singular_export_agent.handle_pending_export(pending_export, session=db_session)

    assert db_session.query(models.ExportTransaction).one().status == ExportTransactionStatus.EXPORT_FAILED
    assert db_session.query(models.PendingExport).one_or_none() is None


@time_machine.travel(pendulum.datetime(2022, 11, 24, 9, 0, 0, 0, "Europe/London"))
def test_retry_pending_export(
    mock_singular_export_agent: MockSingularExportAgent,
    db_session: db.Session,
    export_transaction: models.ExportTransaction,
    pending_export: models.PendingExport,
) -> None:
    mock_singular_export_agent._retry_pending_export(pending_export, pendulum.now().add(minutes=20), session=db_session)

    assert db_session.query(models.PendingExport).one().retry_at == pendulum.datetime(2022, 11, 24, 9, 20).naive()


def test_try_get_result_from_exception_request_exception(mock_singular_export_agent: MockSingularExportAgent):
    response_result = mock_singular_export_agent._try_get_result_from_exception(RequestException(response={}))

    assert response_result == ""


@mock.patch.object(SingularExportAgent, "get_response_result", side_effect=Exception)
def test_try_get_result_from_exception_when_exception_raised(
    mock_get_response_result, mock_singular_export_agent: MockSingularExportAgent
) -> None:
    response_result = mock_singular_export_agent._try_get_result_from_exception(RequestException(response={}))

    assert response_result == ""


@mock.patch.object(SingularExportAgent, "get_response_result", return_value="response")
def test_try_get_result_from_exception(mock_get_response_result, mock_singular_export_agent: MockSingularExportAgent):
    response_result = mock_singular_export_agent._try_get_result_from_exception(RequestException(response={}))

    assert response_result == "response"


def test_delete_pending_export(
    export_transaction: models.ExportTransaction,
    pending_export: models.PendingExport,
    mock_singular_export_agent: MockSingularExportAgent,
    db_session: db.Session,
) -> None:
    assert db_session.query(models.PendingExport).one() == pending_export

    mock_singular_export_agent._delete_pending_export(pending_export, session=db_session)

    assert db_session.query(models.PendingExport).one_or_none() is None


def test_get_response_result(mock_singular_export_agent: MockSingularExportAgent) -> None:
    response = responses.Response(method="POST", url="http://singular_export_agent.test")
    response_result = mock_singular_export_agent.get_response_result(response)

    assert response_result is None


def test_make_export_data_not_implemented(
    mock_singular_export_agent: MockSingularExportAgent, db_session: db.Session
) -> None:
    with pytest.raises(NotImplementedError) as e:
        mock_singular_export_agent.make_export_data(models.MatchedTransaction(), session=db_session)

    assert e.value.args[0] == "Override the make export data method in your export agent"
