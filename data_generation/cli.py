import random
import typing as t
import uuid

from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256

from io import BytesIO
from datetime import datetime

import click

from azure.storage.blob import BlobServiceClient
from kombu import Connection

import settings

from harmonia_fixtures.payment_cards import token_user_info_map
from harness.providers.registry import import_data_providers

from app.feeds import ImportFeedTypes
from app.imports.agents import QueueAgent
from app.imports.agents.bases.base import BaseAgent
from app.imports.agents.bases.file_agent import FileAgent, SftpFileSource
from app.imports.agents.registry import import_agents
from app.reporting import get_logger
from app.service.sftp import SFTP

DEFAULT_NUM_TX = 10000
PAYMENT_AGENT_TO_PROVIDER_SLUG = {
    "visa-auth": "visa",
    "visa-settlement": "visa",
    "mastercard-auth": "mastercard",
    "mastercard-settlement": "mastercard",
    "amex": "amex",
    "amex-auth": "amex",
}
MIDS_MAP = {
    "iceland-bonus-card": {
        "visa": ["2894183", "2894843", "2900453", "2900873", "2901343", "2902153", "2903043", "2903623", "2904273"],
        "mastercard": ["34870233", "34872513", "34873083", "34874053", "34874713", "34875443", "34876093"],
        "amex": ["8174868976", "8174868968", "8042520049", "8042520320", "8174868984", "8174868992"],
    },
    "harvey-nichols": {
        "visa": ["19410121", "19410201", "19410381", "19410461"],
        "mastercard": ["19410121", "19410201", "19410381", "19410461"],
        "amex": ["19410121", "19410201", "19410381", "19410461"],
    },
    "wasabi-club": {
        "visa": ["16433941", "16434021", "15419601", "16434361", "16434511", "16434691", "15819251"],
        "mastercard": ["16433941", "16434021", "15419601", "16434361", "16434511", "16434691", "15819251"],
        "amex": ["9421717158", "9421721788", "9422065326", "9447911868", "9421724592", "9421724626", "9449137736"],
    },
}
logger = get_logger("data-generator")


class DataDumper:
    def __init__(self, agent_instance: BaseAgent, dump_to_stdout: bool = False):
        self.agent = agent_instance
        self.stdout = dump_to_stdout

    def dump(self, data):
        if self.stdout:
            print(data)
            raise SystemExit(0)


class SftpDumper(DataDumper):
    def dump(self, data):
        super().dump(data)
        with SFTP(self.agent.sftp_credentials, self.agent.skey, str(self.agent.Config.path)) as sftp:
            sftp.client.putfo(BytesIO(data), f"{self.agent.provider_slug}-{datetime.now().isoformat()}.csv")


class BlobDumper(DataDumper):
    def dump(self, data):
        super().dump(data)
        bbs = BlobServiceClient.from_connection_string(settings.BLOB_STORAGE_DSN)
        container_name = settings.BLOB_IMPORT_CONTAINER
        blob_client = bbs.get_blob_client(
            container_name, f"{self.agent.Config.path}{self.agent.provider_slug}-{datetime.now().isoformat()}.csv",
        )
        blob_client.upload_blob(data)


class QueueDumper(DataDumper):
    def dump(self, data):
        super().dump(data)
        queue_name = f"""{self.agent.provider_slug}-{('auth'
            if self.agent.feed_type == ImportFeedTypes.AUTH else 'settlement')}"""
        with Connection(settings.RABBITMQ_DSN, connect_timeout=3) as conn:
            q = conn.SimpleQueue(queue_name)
            for message in data:
                q.put(message, headers={"X-Provider": self.agent.provider_slug})


def make_fixture(merchant_slug: str, payment_provider_agent: str, num_tx: int):
    token_users = list(token_user_info_map[merchant_slug].items())
    payment_provider_slug = PAYMENT_AGENT_TO_PROVIDER_SLUG[payment_provider_agent]
    fixture: t.Dict[str, t.Any] = {
        "agents": [{"slug": merchant_slug}, {"slug": payment_provider_agent}],
        "users": [],
        "payment_provider": {"slug": payment_provider_slug},
    }
    for i, (token, user_info) in enumerate(token_users):
        user_data = {
            "loyalty_id": user_info.loyalty_id,
            "token": token,
            "first_six": user_info.card_information.first_six,
            "last_four": user_info.card_information.last_four,
            "transactions": [],
        }
        tx_per_user, remainder = divmod(num_tx, len(token_users))
        if i == 0:
            tx_per_user += remainder
        for _ in range(tx_per_user):
            user_data["transactions"].append(
                {
                    "amount": round(random.randint(100, 9000)),
                    "auth_code": random.randint(100000, 999999),
                    "date": datetime(
                        2020, *[random.randint(a, b) for a, b in [(1, 12), (1, 28), (1, 23), (1, 59), (1, 59)]]
                    ),
                    "settlement_key": sha256(str(uuid.uuid4()).encode()).hexdigest(),
                    "mid": random.choice(MIDS_MAP[merchant_slug][payment_provider_slug]),
                }
            )
        fixture["users"].append(user_data)
    return fixture


def get_data_dumper(agent_instance: BaseAgent, dump_to_stdout: bool = False):
    dumper_class: t.Type[DataDumper]
    if isinstance(agent_instance, FileAgent):
        dumper_class = SftpDumper if isinstance(agent_instance.filesource, SftpFileSource) else BlobDumper
    elif isinstance(agent_instance, QueueAgent):
        dumper_class = QueueDumper
    else:
        raise Exception(f"Unhandled agent type: {agent_instance}")
    return dumper_class(agent_instance, dump_to_stdout=dump_to_stdout)


@click.command()
@click.option("-m", "--merchant-slug", help="merchant slug", required=True)
@click.option("-p", "--payment-provider-agent", help="payment provider agent", required=True)
@click.option("-t", "--num-tx", type=int, default=DEFAULT_NUM_TX, help=f"Default: {DEFAULT_NUM_TX}")
@click.option("-o", "--stdout", help="dump to stdout and exit", is_flag=True)
def generate(merchant_slug: str, payment_provider_agent: str, num_tx: int, stdout: bool = False):
    logger.info(f"Generating fixture for {merchant_slug} & {payment_provider_agent}...")
    fixture = make_fixture(merchant_slug, payment_provider_agent, num_tx)
    logger.info(f"Finished generating fixture for {merchant_slug} & {payment_provider_agent}")

    agent_data = {}
    with ProcessPoolExecutor(max_workers=len(fixture["agents"])) as process_pool:
        for agent in fixture["agents"]:
            agent_slug = agent["slug"]
            data_provider = import_data_providers.instantiate(agent_slug)
            future = process_pool.submit(data_provider.provide, fixture)
            data = future.result()
            agent_data[agent_slug] = data

    for agent_slug, data in agent_data.items():
        logger.info(f"Dumping {agent_slug} data...")
        agent_instance: BaseAgent = import_agents.instantiate(agent_slug)
        dumper = get_data_dumper(agent_instance, dump_to_stdout=stdout)
        dumper.dump(data)
        logger.info(f"Finished dumping {agent_slug} data")


if __name__ == "__main__":
    generate()
