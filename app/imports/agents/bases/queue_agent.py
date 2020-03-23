import typing as t

import kombu.mixins

from app.imports.agents import BaseAgent
import settings


class QueueAgent(BaseAgent):
    def run(self, *, once: bool = False):
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

        queue_name = self.Config.queue_name  # type: ignore
        with kombu.Connection(settings.RABBITMQ_DSN) as conn:
            consumer = Consumer(conn, queue_name, self)
            self.log.info(f"Connected to RabbitMQ, consuming {queue_name}")
            consumer.run()

    def do_import(self, body: dict):
        queue_name = self.Config.queue_name  # type: ignore
        self._import_transactions([body], source=f"AMQP: {queue_name}")


class Consumer(kombu.mixins.ConsumerMixin):
    def __init__(self, connection: kombu.Connection, queue_name: str, agent: QueueAgent):
        self.queue = kombu.Queue(queue_name)
        self.connection = connection
        self.agent = agent

    def get_consumers(self, Consumer: t.Type[kombu.Consumer], _):
        return [Consumer([self.queue], callbacks=[self.on_message], accept=["json"])]

    def on_message(self, body: dict, message: kombu.Message):
        self.agent.log.info(f"Received transaction: {body}")
        self.agent.do_import(body)
        message.ack()
