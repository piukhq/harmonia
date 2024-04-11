import logging
from pathlib import Path, PosixPath
from unittest import mock

import pendulum
import pytest
import time_machine

from app import db
from app.config import KEY_PREFIX, Config, ConfigValue
from app.export_result.agents.bases.results_file_agent import FileSourceBase, ResultsFileAgent
from app.reporting import get_logger

PROVIDER_SLUG = "mock-provider-slug"
PATH_KEY = f"{KEY_PREFIX}results.agents.{PROVIDER_SLUG}.path"
SCHEDULE_KEY = f"{KEY_PREFIX}results.agents.{PROVIDER_SLUG}.schedule"


class MockResultsFileAgent(ResultsFileAgent):
    provider_slug = "mock-provider-slug"

    config = Config(
        ConfigValue("path", key=PATH_KEY, default=f"results/{PROVIDER_SLUG}/"),
        ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *"),
    )


class TestResultFileSourceBase:
    def test_file_source_base_provide_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError) as e:
            FileSourceBase(path=Path(), logger=logging.Logger(name="test_logger")).provide(callback=None)

        assert e.value.args[0] == "FileSourceBase does not implement provide()"


class TestResultFileAgent:
    @time_machine.travel(pendulum.datetime(2024, 4, 9, 9, 45, 0, 0, "UTC"))
    @mock.patch("app.export_result.agents.bases.results_file_agent.bink_prometheus.update_gauge")
    @mock.patch("app.export_result.agents.bases.results_file_agent.bink_prometheus.increment_counter")
    def test_update_file_metrics(self, mock_increment_counter, mock_update_gauge) -> None:
        agent = MockResultsFileAgent()
        timestamp = pendulum.now().int_timestamp
        agent._update_file_metrics(timestamp)

        assert mock_increment_counter.call_args.kwargs == {
            "agent": agent,
            "counter_name": "files_received",
            "increment_by": 1,
            "process_type": "results",
            "slug": "mock-provider-slug",
        }
        assert mock_update_gauge.call_args.kwargs == {
            "agent": agent,
            "gauge_name": "last_file_timestamp",
            "value": timestamp,
            "process_type": "results",
            "slug": "mock-provider-slug",
        }

    def test_format_audit_transaction_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            MockResultsFileAgent().format_audit_transaction(data=b"")

    def test_fileagent_config(self, db_session: db.Session) -> None:
        with mock.patch("app.export_result.agents.bases.results_file_agent.db.session_scope", return_value=db_session):
            file_agent_config = MockResultsFileAgent().fileagent_config

        assert file_agent_config == ResultsFileAgent._FileAgentConfig(
            path="results/mock-provider-slug/", schedule="* * * * *"
        )

    def test_filesource(self) -> None:
        filesource = MockResultsFileAgent().filesource

        assert filesource.path == PosixPath("files/imports/results/mock-provider-slug")
        assert filesource.log == get_logger("export-result-agent.mock-provider-slug")

    @mock.patch("app.scheduler.CronScheduler.run")
    def test_run(self, mock_cron_scheduler_run, caplog) -> None:
        caplog.set_level(logging.DEBUG)
        agent = MockResultsFileAgent()
        agent.log.propagate = True
        agent.run()

        mock_cron_scheduler_run.assert_called_once()
        assert caplog.messages == [
            "Watching files/imports/results/mock-provider-slug for export result files via LocalFileSource.",
            "Using leader election name: mock-provider-slug-export-result-load",
            "Beginning CronScheduler with schedule '* * * * *'.",
        ]
