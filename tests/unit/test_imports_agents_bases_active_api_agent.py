from unittest import mock

from app import db
from app.config import KEY_PREFIX, Config, ConfigValue
from app.feeds import FeedType
from app.imports.agents.bases.active_api_agent import ActiveAPIAgent

PROVIDER_SLUG = "mock-provider-slug"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"
SCHEDULE_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.schedule"


class MockActiveAPIAgent(ActiveAPIAgent):
    provider_slug = "mock-provider-slug"
    feed_type = FeedType.AUTH

    config = Config(
        ConfigValue("path", key=PATH_KEY, default=f"{PROVIDER_SLUG}/"),
        ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *"),
    )


def test_schedule(db_session: db.Session) -> None:
    with mock.patch("app.imports.agents.bases.active_api_agent.db.session_scope", return_value=db_session):
        schedule = MockActiveAPIAgent().schedule

    assert schedule == "* * * * *"


@mock.patch.object(ActiveAPIAgent, "do_import")
@mock.patch("app.scheduler.CronScheduler.run")
def test_run(mock_cron_scheduler_run, mock_do_import, db_session: db.Session) -> None:
    MockActiveAPIAgent().run()

    mock_cron_scheduler_run.assert_called_once()
