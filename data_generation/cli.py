import random
import typing as t
import uuid

from concurrent.futures import ProcessPoolExecutor

from io import BytesIO
from datetime import datetime, timedelta

import click
import pendulum

from azure.storage.blob import BlobServiceClient
from kombu import Connection
from sqlalchemy.orm.session import Session

import settings

from harmonia_fixtures.payment_cards import token_user_info_map
from harness.providers.registry import import_data_providers

from app import db
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
STORE_ID_MIDS_MAP = {  # type: t.Dict[str, t.Any]
    "iceland-bonus-card": {
        None: {  # store_id
            "visa": ["02894183", "02894843", "02900453", "02900873", "02901343", "02902153", "02903043", "02903623"],
            "mastercard": ["34870233", "34872513", "34873083", "34874053", "34874713", "34875443", "34876093"],
            "amex": ["8174868976", "8174868968", "8042520049", "8042520320", "8174868984", "8174868992"],
        },
    },
    "harvey-nichols": {
        "0001017   005682": {  # store_id
            "amex": ["9421355991", "9423447317", "9425544541", "9448629014"],
            "mastercard": ["3553323", "3561503", "3561683", "3561763", "3561843", "3561923", "3562073", "3562233"],
            "visa": ["56742051", "80289201", "80289611", "92040173", "92040913"],
        },
    },
    "wasabi-club": {
        None: {  # store_id
            "visa": ["16433941", "16434021", "15419601", "16434361", "16434511", "16434691", "15819251"],
            "mastercard": ["16433941", "16434021", "15419601", "16434361", "16434511", "16434691", "15819251"],
            "amex": ["9421717158", "9421721788", "9422065326", "9447911868", "9421724592", "9421724626", "9449137736"],
        },
    },
}

logger = get_logger("data-generator")


class PathConfigMixin:
    def get_path(self, session: Session):
        return self.agent.config.get("path", session=session)


class DataDumper:
    def __init__(self, agent_instance: BaseAgent, num_payment_tx: int = None, dump_to_stdout: bool = False):
        self.agent = agent_instance
        self.num_payment_tx = num_payment_tx
        self.stdout = dump_to_stdout


class SftpDumper(DataDumper, PathConfigMixin):
    def dump(self, data, *, session: Session):
        if self.stdout:
            print(data)
            return

        with SFTP(self.agent.sftp_credentials, self.agent.skey, self.get_path(session=session)) as sftp:
            sftp.client.putfo(BytesIO(data), f"{self.agent.provider_slug}-{datetime.now().isoformat()}.csv")


class BlobDumper(DataDumper, PathConfigMixin):
    def dump(self, data, *, session: Session):
        if self.stdout:
            print(data)
            return

        bbs = BlobServiceClient.from_connection_string(settings.BLOB_STORAGE_DSN)
        container_name = settings.BLOB_IMPORT_CONTAINER
        blob_client = bbs.get_blob_client(
            container_name,
            f"{self.get_path(session=session)}{self.agent.provider_slug}-{datetime.now().isoformat()}.csv",
        )
        blob_client.upload_blob(data)


class QueueDumper(DataDumper):
    def dump(self, data, *, session: Session):
        if self.stdout:
            print(data)
            return

        if self.agent.feed_type in (ImportFeedTypes.AUTH, ImportFeedTypes.SETTLED):
            queue_name = f"""{self.agent.provider_slug}-{('auth'
                if self.agent.feed_type == ImportFeedTypes.AUTH else 'settlement')}"""
        else:
            raise Exception(f"Unsupported ImportFeedType: {self.agent.feed_type}")
        logger.info(
            f"Adding {min((len(data), self.num_payment_tx))} {self.agent.provider_slug} messages to the queue..."
        )
        with Connection(settings.RABBITMQ_DSN, connect_timeout=3) as conn:
            q = conn.SimpleQueue(queue_name)
            for i, message in enumerate(data):
                if i < self.num_payment_tx:
                    q.put(message, headers={"X-Provider": self.agent.provider_slug})


def make_fixture(merchant_slug: str, payment_provider_agent: str, num_tx: int):
    token_users = list(token_user_info_map[merchant_slug].items())
    payment_provider_slug = PAYMENT_AGENT_TO_PROVIDER_SLUG[payment_provider_agent]
    fixture: t.Dict[str, t.Any] = {
        "agents": [{"slug": payment_provider_agent}, {"slug": merchant_slug}],
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
            store_id = random.choice(  # will allow us to add more HN (+ perhaps WHSmith) store IDs if required
                list(STORE_ID_MIDS_MAP[merchant_slug].keys())
            )
            mid_map = STORE_ID_MIDS_MAP[merchant_slug][store_id]
            user_data["transactions"].append(
                {
                    "amount": round(random.randint(100, 9000)),
                    "auth_code": random.randint(100000, 999999),
                    "date": pendulum.now()
                    - timedelta(
                        **{
                            "days": random.randint(1, 30 * 3),
                            "hours": random.randint(0, 23),
                            "minutes": random.randint(0, 60),
                            "seconds": random.randint(0, 60),
                        }
                    ),
                    "settlement_key": str(uuid.uuid4()),
                    "mid": random.choice(mid_map[payment_provider_slug]),
                    "store_id": store_id,
                }
            )
        fixture["users"].append(user_data)
    return fixture


def get_data_dumper(agent_instance: BaseAgent, dump_to_stdout: bool = False, num_payment_tx: int = None):
    dumper_class: t.Type[DataDumper]
    if isinstance(agent_instance, FileAgent):
        dumper_class = SftpDumper if isinstance(agent_instance.filesource, SftpFileSource) else BlobDumper
    elif isinstance(agent_instance, QueueAgent):
        dumper_class = QueueDumper
    else:
        raise Exception(f"Unhandled agent type: {agent_instance}")
    return dumper_class(agent_instance, num_payment_tx=num_payment_tx, dump_to_stdout=dump_to_stdout)


@click.command()
@click.option("-m", "--merchant-slug", help="merchant slug", required=True)
@click.option("-p", "--payment-provider-agent", help="payment provider agent", required=True)
@click.option(
    "-M",
    "--num-merchant-tx",
    type=int,
    default=DEFAULT_NUM_TX,
    help=f"Number of merchant transactions to make. Default: {DEFAULT_NUM_TX}",
)
@click.option(
    "-P",
    "--num-payment-tx",
    type=int,
    default=DEFAULT_NUM_TX,
    help=f"Number of payment transactions to make. Default: {DEFAULT_NUM_TX}",
)
@click.option("-o", "--stdout", help="dump to stdout and exit", is_flag=True)
def generate(
    merchant_slug: str, payment_provider_agent: str, num_merchant_tx: int, num_payment_tx: int, stdout: bool = False
):
    logger.info(f"Generating fixture for {merchant_slug} & {payment_provider_agent}...")
    fixture = make_fixture(merchant_slug, payment_provider_agent, num_merchant_tx)
    logger.info(f"Finished generating fixture for {merchant_slug} & {payment_provider_agent}")

    agent_data = {}
    with ProcessPoolExecutor(max_workers=len(fixture["agents"])) as process_pool:
        futures = {}
        logger.info("Starting data generation.")
        for agent in fixture["agents"]:
            agent_slug = agent["slug"]
            data_provider = import_data_providers.instantiate(agent_slug)
            futures[agent_slug] = process_pool.submit(data_provider.provide, fixture)
            logger.info(f"Task queued for {agent_slug}.")

        logger.info("Waiting for data generation to complete...")
        for agent_slug, future in futures.items():
            data = future.result()
            agent_data[agent_slug] = data
            logger.info(f"{agent_slug} data generation completed.")

    with db.session_scope() as session:
        for agent_slug, data in agent_data.items():
            if not click.confirm(f"\nConfirm {agent_slug} data dump", default=True):
                break
            logger.info(f"Dumping {agent_slug} data...")
            agent_instance: BaseAgent = import_agents.instantiate(agent_slug)
            dumper = get_data_dumper(agent_instance, num_payment_tx=num_payment_tx, dump_to_stdout=stdout)
            dumper.dump(data, session=session)
            logger.info(f"Finished dumping {agent_slug} data")


if __name__ == "__main__":
    generate()
