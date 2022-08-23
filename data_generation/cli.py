import csv
import random
import typing as t
import uuid
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

import click
import pendulum
from azure.storage.blob import BlobServiceClient
from harmonia_fixtures.payment_cards import token_user_info_map
from kombu import Connection
from sqlalchemy.orm.session import Session

import settings
from app import db
from app.feeds import FeedType
from app.imports.agents.bases.base import BaseAgent
from app.imports.agents.bases.file_agent import FileAgent, SftpFileSource
from app.imports.agents.bases.queue_agent import QueueAgent
from app.imports.agents.registry import import_agents
from app.reporting import get_logger
from app.service.sftp import SFTP
from harness.providers.registry import BaseImportDataProvider, import_data_providers

DEFAULT_NUM_TX = 10000
PAYMENT_AGENT_TO_PROVIDER_SLUG = {
    "visa-auth": "visa",
    "visa-settlement": "visa",
    "visa-refund": "visa",
    "mastercard-auth": "mastercard",
    "mastercard-settlement": "mastercard",
    "amex-auth": "amex",
    "amex-settlement": "amex",
}

# merchants_with_location_ids contains merchants that require a location id to locate MID's
# Added this because some Iceland data in merchant identifier table had location id's but these are not used.
merchants_with_location_ids = [
    "harvey-nichols",
]

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
    def dump(self, dataset: list[bytes], *, session: Session):
        if self.stdout:
            for data in dataset:
                print(data)
            return

        with SFTP(self.agent.sftp_credentials, self.agent.skey, self.get_path(session=session)) as sftp:
            for i, data in enumerate(dataset):
                sftp.client.putfo(BytesIO(data), f"{self.agent.provider_slug}-{datetime.now().isoformat()}-{i}.csv")


class BlobDumper(DataDumper, PathConfigMixin):
    def dump(self, dataset: list[bytes], *, session: Session):
        if self.stdout:
            for data in dataset:
                print(data)
            return

        bbs = BlobServiceClient.from_connection_string(settings.BLOB_STORAGE_DSN)
        container_name = settings.BLOB_IMPORT_CONTAINER

        for i, data in enumerate(dataset):
            blob_client = bbs.get_blob_client(
                container_name,
                f"{self.get_path(session=session)}{self.agent.provider_slug}-{datetime.now().isoformat()}-{i}.csv",
            )
            blob_client.upload_blob(data)


class QueueDumper(DataDumper):
    def dump(self, dataset: list[list[dict]], *, session: Session):
        if self.stdout:
            for data in dataset:
                print(data)
            return

        if self.agent.feed_type in (FeedType.AUTH, FeedType.SETTLED):
            queue_name = f"""{self.agent.provider_slug}-{('auth'
                if self.agent.feed_type == FeedType.AUTH else 'settlement')}"""
        else:
            raise Exception(f"Unsupported ImportFeedType: {self.agent.feed_type}")

        data = (message for message_list in dataset for message in message_list)

        logger.info(f"Adding up to {self.num_payment_tx} {self.agent.provider_slug} messages to the queue...")

        with Connection(settings.RABBITMQ_DSN, connect_timeout=3) as conn:
            q = conn.SimpleQueue(queue_name)
            for i, message in enumerate(data):
                if i >= self.num_payment_tx:
                    break
                q.put(message, headers={"X-Provider": self.agent.provider_slug})


def batch_provide(data_provider: BaseImportDataProvider, fixture: dict, batch_size: int) -> list[bytes]:
    dataset = []

    def produce_file(fixture: dict):
        dataset.append(data_provider.provide(fixture))

    def make_blank_fixture_users():
        return [
            {
                "loyalty_id": user["loyalty_id"],
                "token": user["token"],
                "first_six": user["first_six"],
                "last_four": user["last_four"],
                "transactions": [],
            }
            for user in fixture["users"]
        ]

    def make_blank_fixture():
        return {
            "agents": fixture["agents"],
            "payment_provider": fixture["payment_provider"],
            "users": make_blank_fixture_users(),
        }

    def reset(fixture: dict):
        for user in fixture["users"]:
            user["transactions"] = []

    batch_fixture = make_blank_fixture()
    batch_counter = 0
    for user_idx, user in enumerate(fixture["users"]):
        for transaction in user["transactions"]:
            batch_fixture["users"][user_idx]["transactions"].append(transaction)

            batch_counter += 1
            if batch_counter >= batch_size:
                produce_file(batch_fixture)
                reset(batch_fixture)
                batch_counter = 0

    # clear up any stragglers
    if batch_counter > 0:
        produce_file(batch_fixture)

    return dataset


def mids_data(merchant_slug: str, payment_slug: str) -> dict:
    # Load mid and location id from csv files for a single merchant
    # Only harvey nichols uses location id's to locate MID's so special check in this code.
    filename = f"{merchant_slug}-mids.csv"
    file_path = Path.cwd() / "data_generation/files" / filename
    location_payment_mids = defaultdict(list)

    with file_path.open() as f:
        data = csv.reader(f, delimiter=",")
        for row in data:
            if not payment_slug == row[0]:
                continue

            location_id = row[3] if merchant_slug in merchants_with_location_ids else None
            location_payment_mids[location_id].append(row[1])

    return location_payment_mids


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

        location_payment_mids = mids_data(merchant_slug, payment_provider_slug)
        tx_per_user, remainder = divmod(num_tx, len(token_users))
        if i == 0:
            tx_per_user += remainder
        for _ in range(tx_per_user):
            location_id = random.choice(  # will allow us to add more HN (+ perhaps WHSmith) location IDs if required
                list(location_payment_mids.keys())
            )
            mid_map = location_payment_mids[location_id]
            user_data["transactions"].append(
                {
                    "amount": round(random.randint(100, 30000)),
                    "auth_code": random.randint(100000, 999999),
                    "date": pendulum.now()
                    - timedelta(
                        **{
                            "days": random.randint(1, 3),
                            "hours": random.randint(0, 23),
                            "minutes": random.randint(0, 60),
                            "seconds": random.randint(0, 60),
                        }
                    ),
                    "settlement_key": str(uuid.uuid4()),
                    "identifier": random.choice(mid_map),
                    "location_id": location_id,
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
@click.option(
    "-b",
    "--batch-size",
    type=int,
    default=DEFAULT_NUM_TX,
    help=f"File batch size. Default: {DEFAULT_NUM_TX}",
)
@click.option("-o", "--stdout", help="dump to stdout and exit", is_flag=True)
def generate(
    merchant_slug: str,
    payment_provider_agent: str,
    num_merchant_tx: int,
    num_payment_tx: int,
    batch_size: int,
    stdout: bool = False,
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
            futures[agent_slug] = process_pool.submit(batch_provide, data_provider, fixture, batch_size)
            logger.info(f"Task queued for {agent_slug}.")

        logger.info("Waiting for data generation to complete...")
        for agent_slug, future in futures.items():
            agent_data[agent_slug] = future.result()
            logger.info(f"{agent_slug} data generation completed.")

    with db.session_scope() as session:
        for agent_slug, dataset in agent_data.items():
            if not click.confirm(f"\nConfirm {agent_slug} data dump", default=True):
                break
            logger.info(f"Dumping {agent_slug} data...")
            agent_instance: BaseAgent = import_agents.instantiate(agent_slug)
            dumper = get_data_dumper(agent_instance, num_payment_tx=num_payment_tx, dump_to_stdout=stdout)
            dumper.dump(dataset, session=session)
            logger.info(f"Finished dumping {agent_slug} data")


if __name__ == "__main__":
    generate()
