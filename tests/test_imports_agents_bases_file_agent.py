import logging
from pathlib import Path, PosixPath
from unittest import mock

import pendulum
import pytest
import time_machine

from app import db
from app.config import KEY_PREFIX, Config, ConfigValue
from app.feeds import FeedType
from app.imports.agents.bases.file_agent import FileAgent, FileSourceBase, LocalFileSource
from app.reporting import get_logger

PROVIDER_SLUG = "mock-provider-slug"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"
SCHEDULE_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.schedule"


class MockFileAgent(FileAgent):
    provider_slug = "mock-provider-slug"
    feed_type = FeedType.SETTLED

    config = Config(
        ConfigValue("path", key=PATH_KEY, default=f"{PROVIDER_SLUG}/"),
        ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *"),
    )


class TestFileSourceBase:
    def test_file_source_base_provide_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError) as e:
            FileSourceBase(path=Path(), logger=logging.Logger(name="test_logger")).provide(callback=None)

        assert e.value.args[0] == "FileSourceBase does not implement provide()"


class TestFileAgent:
    @time_machine.travel(pendulum.datetime(2022, 11, 24, 9, 0, 0, 0, "UTC"))
    @mock.patch("app.imports.agents.bases.file_agent.bink_prometheus.update_gauge")
    @mock.patch("app.imports.agents.bases.file_agent.bink_prometheus.increment_counter")
    def test_update_file_metrics(self, mock_increment_counter, mock_update_gauge) -> None:
        agent = MockFileAgent()
        agent._update_file_metrics(pendulum.now().int_timestamp)

        assert mock_increment_counter.call_args.kwargs == {
            "agent": agent,
            "counter_name": "files_received",
            "increment_by": 1,
            "process_type": "import",
            "slug": "mock-provider-slug",
        }
        assert mock_update_gauge.call_args.kwargs == {
            "agent": agent,
            "gauge_name": "last_file_timestamp",
            "value": 1669280400,
            "process_type": "import",
            "slug": "mock-provider-slug",
        }

    def test_yield_transactions_data_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            MockFileAgent().yield_transactions_data(data=b"")

    def test_get_transaction_date_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            MockFileAgent().get_transaction_date(data={})

    def test_fileagent_config(self, db_session: db.Session) -> None:
        with mock.patch("app.imports.agents.bases.file_agent.db.session_scope", return_value=db_session):
            file_agent_config = MockFileAgent().fileagent_config

        assert file_agent_config == FileAgent._FileAgentConfig(path="mock-provider-slug/", schedule="* * * * *")

    def test_filesource(self) -> None:
        filesource = MockFileAgent().filesource

        assert filesource.path == PosixPath("files/imports/mock-provider-slug")
        assert filesource.log == get_logger("import-agent.mock-provider-slug")

    @mock.patch("app.scheduler.CronScheduler.run")
    def test_run(self, mock_cron_scheduler_run, caplog) -> None:
        caplog.set_level(logging.DEBUG)
        agent = MockFileAgent()
        agent.log.propagate = True
        agent.run()

        mock_cron_scheduler_run.assert_called_once()
        assert caplog.messages == [
            "Watching files/imports/mock-provider-slug for files via LocalFileSource.",
            "Using leader election name: mock-provider-slug-settled-import",
            "Beginning CronScheduler with schedule '* * * * *'.",
        ]

    def has_capacity_yielder(self) -> bool:
        yield False
        yield True

    @mock.patch.object(LocalFileSource, "provide")
    @mock.patch("app.imports.agents.bases.file_agent.tasks.import_queue.has_capacity")
    def test_callback_import_queue_is_at_capacity(self, mock_has_capacity, mock_provide, caplog) -> None:
        mock_has_capacity.side_effect = self.has_capacity_yielder()
        caplog.set_level(logging.DEBUG)
        agent = MockFileAgent()
        agent.log.propagate = True
        agent.callback()

        assert mock_has_capacity.call_count == 2
        mock_provide.assert_called_once()
        assert caplog.messages == ["Import queue is at capacity. Suspending for a second."]

    @mock.patch.object(LocalFileSource, "provide")
    @mock.patch("app.imports.agents.bases.file_agent.retry.exponential_delay")
    @mock.patch("app.imports.agents.bases.file_agent.tasks.import_queue.has_capacity", return_value=True)
    def test_callback_import_queue_has_capacity(
        self, mock_has_capacity, mock_retry_exponential_delay, mock_provide
    ) -> None:
        MockFileAgent().callback()

        mock_has_capacity.assert_called_once()
        mock_retry_exponential_delay.assert_not_called()
        mock_provide.assert_called_once()
