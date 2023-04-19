import typing as t
from functools import cached_property

import kombu.mixins

import settings
from app import db
from app.imports.agents.bases.base import BaseAgent


class QueueAgent(BaseAgent):
    @cached_property
    def queue_name(self):
        with db.session_scope() as session:
            qn = self.config.get("queue_name", session=session)
        return qn

    def run(self):
        required_settings = [
            "RABBITMQ_HOST",
            "RABBITMQ_PORT",
            "RABBITMQ_USER",
            "RABBITMQ_PASS",
        ]
        if any(getattr(settings, s, None) is None for s in required_settings):
            raise settings.ConfigVarRequiredError(
                f"{type(self).__name__} requires that all of the following settings are set: "
                f"{', '.join(required_settings)}"
            )

        with kombu.Connection(settings.RABBITMQ_DSN) as conn:
            consumer = Consumer(conn, self.queue_name, self)
            self.log.info(f"Connected to RabbitMQ, consuming {self.queue_name}")
            consumer.run()

    def _do_import(self, body: dict):
        # TODO: this is less than ideal - should we keep a session open?
        with db.session_scope() as session:
            list(self._import_transactions([body], source=f"AMQP: {self.queue_name}", session=session))


class Consumer(kombu.mixins.ConsumerMixin):
    def __init__(self, connection: kombu.Connection, queue_name: str, agent: QueueAgent):
        self.queue = kombu.Queue(queue_name)
        self.connection = connection
        self.agent = agent

    def get_consumers(self, Consumer: t.Type[kombu.Consumer], _):
        return [Consumer([self.queue], callbacks=[self.on_message], accept=["json"])]

    def on_message(self, body: str, message: kombu.Message):
        self.agent.log.info(f"Received transaction: {body}")
        self.agent._do_import(body)
        message.ack()
