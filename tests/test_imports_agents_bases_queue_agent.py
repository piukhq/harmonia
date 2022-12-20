import logging
from unittest import mock

import kombu.mixins
import pytest

import settings
from app import db, models
from app.imports.agents.bases.queue_agent import Consumer
from app.imports.agents.visa import VisaAuth
from tests.fixtures import SampleTransactions


def test_queue_agent_queue_name() -> None:
    assert VisaAuth().queue_name == "visa-auth"


@mock.patch.object(Consumer, "run")
def test_queue_agent_run(mock_run, caplog) -> None:
    agent = VisaAuth()
    caplog.set_level(logging.DEBUG)
    agent.log.propagate = True
    agent.run()

    assert mock_run.call_count == 1
    assert caplog.messages[0] == "Connected to RabbitMQ, consuming visa-auth"


def test_queue_agent_run_missing_settings() -> None:
    settings.RABBITMQ_HOST = None
    with pytest.raises(settings.ConfigVarRequiredError) as e:
        VisaAuth().run()

    assert (
        e.value.args[0] == "VisaAuth requires that all of the following settings are set: "
        "RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASS"
    )


def test_queue_agent_do_import(db_session: db.Session) -> None:
    agent = VisaAuth()
    agent._do_import(SampleTransactions().visa_auth())

    assert db_session.query(models.ImportTransaction.transaction_id).one()[0] == "db0b14a3-0ca8-4281-9a77-57b5b88ec0a4"


def test_consumer_get_consumers() -> None:
    # agent = VisaAuth()
    # with kombu.Connection(settings.RABBITMQ_DSN) as conn:
    #     consumer = Consumer(conn, "visa-auth", agent)
    # consumers = consumer.get_consumers(kombu.Consumer, "")
    pass


def test_consumer_on_message() -> None:
    pass
