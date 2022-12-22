import logging
from pathlib import Path
from unittest import mock

import pytest

from app import db
from app.config import KEY_PREFIX, Config, ConfigValue

from app.feeds import FeedType
from app.imports.agents.bases.file_agent import FileSourceBase, LocalFileSource, FileAgent

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
    def test_do_import(self, caplog) -> None:
        pass

    def test_update_file_metrics(self) -> None:
        pass

    def test_yield_transactions_data_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            FileAgent().yield_transactions_data(data=b'')

    def test_get_transaction_date_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            FileAgent().get_transaction_date(data={})

    def test_fileagent_config(self, db_session: db.Session) -> None:
        with mock.patch("app.imports.agents.bases.file_agent.db.session_scope", return_value=db_session):
            file_agent_config = MockFileAgent().fileagent_config

        pass

    def test_filesource(self) -> None:
        pass

    def test_run(self) -> None:
        pass

    def test_callback(self) -> None:
        pass
