import pytest

from app import db, models
from app.exports.agents import AgentExportData, BaseAgent
from app.exports.models import ExportTransactionStatus
from tests.unit.fixtures import get_or_create_export_transaction, get_or_create_pending_export

MERCHANT_SLUG = "mock-base-agent"


class MockBaseAgent(BaseAgent):
    provider_slug = MERCHANT_SLUG


@pytest.fixture
def mock_base_agent() -> MockBaseAgent:
    return MockBaseAgent()


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


def make_export_data(export_transaction) -> AgentExportData:
    return AgentExportData(
        outputs=[],
        transactions=[export_transaction],
        extra_data={},
    )


@pytest.fixture
def export_data(export_transaction: models.ExportTransaction) -> AgentExportData:
    return make_export_data(export_transaction)


def test_provider_slug_not_implemented() -> None:
    with pytest.raises(NotImplementedError) as e:
        BaseAgent()

    assert e.value.args[0] == "BaseAgent is missing a required property: provider_slug"


def test_repr(mock_base_agent: MockBaseAgent) -> None:
    repr = mock_base_agent.__repr__()

    assert repr == "MockBaseAgent(provider_slug=mock-base-agent)"


def test_str(mock_base_agent: MockBaseAgent) -> None:
    str = mock_base_agent.__str__()

    assert str == "export agent MockBaseAgent for mock-base-agent"


def test_run_not_implemented(mock_base_agent: MockBaseAgent) -> None:
    with pytest.raises(NotImplementedError) as e:
        mock_base_agent.run()

    assert e.value.args[0] == "This method should be overridden by specialised base agents."


def test_handle_pending_export_not_implemented(
    mock_base_agent: MockBaseAgent, pending_export: models.PendingExport, db_session: db.Session
) -> None:
    with pytest.raises(NotImplementedError) as e:
        mock_base_agent.handle_pending_export(pending_export, session=db_session)

    assert e.value.args[0] == "This method should be overridden by specialised base agents."


def test_export_not_implemented(
    mock_base_agent: MockBaseAgent, export_data: AgentExportData, db_session: db.Session
) -> None:
    with pytest.raises(NotImplementedError) as e:
        mock_base_agent.export(export_data, session=db_session)

    assert (
        e.value.args[0]
        == "Override the export method in your agent to act as the entry point into the singular export process."
    )


def test_export_all_not_implemented(mock_base_agent: MockBaseAgent, db_session: db.Session) -> None:
    with pytest.raises(NotImplementedError) as e:
        mock_base_agent.export_all(session=db_session)

    assert (
        e.value.args[0]
        == "Override the export_all method in your agent to act as the entry point into the batch export process."
    )


def test_save_export_transactions(
    mock_base_agent: MockBaseAgent,
    export_data: AgentExportData,
    export_transaction: models.ExportTransaction,
    db_session: db.Session,
) -> None:
    assert db_session.query(models.ExportTransaction).one().status == ExportTransactionStatus.PENDING

    mock_base_agent._save_export_transactions(export_data, session=db_session)

    assert db_session.query(models.ExportTransaction).one().status == ExportTransactionStatus.EXPORTED


def test_update_metrics_not_implemented(
    mock_base_agent: MockBaseAgent, export_data: AgentExportData, db_session: db.Session
) -> None:
    with pytest.raises(NotImplementedError) as e:
        mock_base_agent._update_metrics(export_data, session=db_session)

    assert e.value.args[0] == "This method should be overridden by specialised base agents."
