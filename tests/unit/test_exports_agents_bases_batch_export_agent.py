import logging
from unittest import mock

import pytest

from app import db, models
from app.config import KEY_PREFIX, Config, ConfigValue
from app.exports.agents import AgentExportData, BatchExportAgent
from tests.unit.fixtures import get_or_create_export_transaction, get_or_create_pending_export

MERCHANT_SLUG = "mock-batch-export-agent"
SCHEDULE_KEY = f"{KEY_PREFIX}agents.exports.{MERCHANT_SLUG}.schedule"
BATCH_SIZE_KEY = f"{KEY_PREFIX}agents.exports.{MERCHANT_SLUG}.batch_size"


class MockBatchExportAgent(BatchExportAgent):
    provider_slug = MERCHANT_SLUG

    config = Config(
        ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *"),
        ConfigValue("batch_size", key=BATCH_SIZE_KEY, default="200"),
    )

    def __init__(self):
        super().__init__()


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


def test_schedule(db_session: db.Session) -> None:
    schedule = MockBatchExportAgent().schedule

    assert schedule == "* * * * *"


@mock.patch("app.scheduler.CronScheduler.run")
def test_run(mock_cron_scheduler_run, db_session: db.Session, caplog) -> None:
    caplog.set_level(logging.DEBUG)
    agent = MockBatchExportAgent()
    agent.log.propagate = True
    agent.run()

    assert "Beginning schedule CronScheduler with schedule '* * * * *'." in caplog.messages
    mock_cron_scheduler_run.assert_called_once()


def test_handle_pending_export(pending_export: models.PendingExport, db_session: db.Session, caplog) -> None:
    caplog.set_level(logging.DEBUG)
    agent = MockBatchExportAgent()
    agent.log.propagate = True
    agent.handle_pending_export(pending_export, session=db_session)

    assert (
        caplog.messages[0] == f"Ignoring PendingExport(id={pending_export.id}, "
        f"export_transaction_id={pending_export.export_transaction_id}) for batch export."
    )


@mock.patch.object(BatchExportAgent, "export_all")
def test_callback(mock_export_all, db_session: db.Session) -> None:
    MockBatchExportAgent().callback()

    mock_export_all.assert_called_once()


def test_yield_export_data_not_implemented(db_session: db.Session) -> None:
    with pytest.raises(NotImplementedError) as e:
        MockBatchExportAgent().yield_export_data(models.MatchedTransaction(), session=db_session)

    assert e.value.args[0] == "Override the yield_export_data method in your agent."


def test_send_export_data_not_implemented(export_transaction: models.ExportTransaction, db_session: db.Session) -> None:
    export_data = make_export_data(export_transaction)
    with pytest.raises(NotImplementedError) as e:
        MockBatchExportAgent().send_export_data(export_data, session=db_session)

    assert e.value.args[0] == "Override the send_export_data method in your agent."
