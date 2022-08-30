import json
import time
import typing as t
from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock
from uuid import uuid4

import click
import pendulum
import rq
import soteria.configuration
import soteria.security
import toml
from azure.keyvault.secrets import SecretClient
from marshmallow import ValidationError, fields, pre_load, validate
from marshmallow.schema import Schema
from prettyprinter import cpprint

from app.api import auth
from app.prometheus import prometheus_thread


@contextmanager
def mocked_auth_decorator():
    # replace the requires_auth decorator with a no-op
    auth.auth_decorator = lambda: lambda *args, **kwargs: lambda fn: fn
    yield


with mocked_auth_decorator():
    import settings
    from app import db, encryption, feeds, models, tasks
    from app.exports.agents import BatchExportAgent, export_agents
    from app.imports.agents.bases.active_api_agent import ActiveAPIAgent
    from app.imports.agents.bases.base import BaseAgent
    from app.imports.agents.bases.file_agent import FileAgent
    from app.imports.agents.bases.queue_agent import QueueAgent
    from app.imports.agents.registry import import_agents
    from app.registry import NoSuchAgent
    from app.service.hermes import hermes
    from harness.providers.registry import import_data_providers

# most of the export agents need this to be set to something.
settings.EUROPA_URL = ""
settings.VAULT_URL = ""
settings.AUDIT_EXPORTS = False


PGP_PUBLIC_KEY = """-----BEGIN PGP PUBLIC KEY BLOCK-----

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
Qo5m6KbOs+AhyFcnj/yGlLeqbA==
=BryC
-----END PGP PUBLIC KEY BLOCK-----
"""

PGP_PRIVATE_KEY = """-----BEGIN PGP PRIVATE KEY BLOCK-----

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
=K3FC
-----END PGP PRIVATE KEY BLOCK-----
"""


class ImportAgentKind(Enum):
    ACTIVE_API = "Active API"
    FILE = "File"
    QUEUE = "Queue"


_import_agent_kind = {
    ActiveAPIAgent: ImportAgentKind.ACTIVE_API,
    FileAgent: ImportAgentKind.FILE,
    QueueAgent: ImportAgentKind.QUEUE,
}


class IdentityDateTimeField(fields.DateTime):
    def _deserialize(self, value, attr, data, **kwargs):
        if isinstance(value, datetime):
            return value
        return super()._deserialize(value, attr, data, **kwargs)


class FixtureUserTransactionSchema(Schema):
    date = IdentityDateTimeField(required=True, allow_none=False)
    amount = fields.Integer(required=True, allow_none=False, strict=True)
    auth_code = fields.String(validate=validate.Length(equal=6))
    merchant_overrides = fields.Dict(required=False)
    payment_provider_overrides = fields.Dict(required=False)
    identifier = fields.String(required=True, allow_none=False)
    identifier_type = fields.String(required=True, allow_none=False)
    location_id = fields.String(required=False, allow_none=True)

    @pre_load
    def convert_dates(self, data, **kwargs):
        # TomlTz objects don't have deepcopy support (for fixture overriding)
        data["date"] = pendulum.instance(data["date"])
        for override in ("merchant_overrides", "payment_provider_overrides"):
            if override in data and "date" in data[override]:
                data[override]["date"] = pendulum.instance(data[override]["date"])
        return data


class FixtureUserSchema(Schema):
    token = fields.String(required=True, allow_none=False, validate=validate.Length(min=1))
    loyalty_id = fields.String(required=True, allow_none=False, validate=validate.Length(min=1))
    first_six = fields.String(required=True, allow_none=False, validate=validate.Length(equal=6))
    last_four = fields.String(required=True, allow_none=False, validate=validate.Length(equal=4))
    credentials = fields.Dict(required=True, allow_none=False)
    transactions = fields.Nested(FixtureUserTransactionSchema, many=True)
    expiry_month = fields.Integer()
    expiry_year = fields.Integer()


class FixtureProviderSchema(Schema):
    slug = fields.String(required=True, allow_none=False, validate=validate.Length(min=1))


class FixtureSchema(Schema):
    location = fields.String(required=True, allow_none=False)
    postcode = fields.String(required=True, allow_none=False)
    loyalty_scheme = fields.Nested(FixtureProviderSchema)
    payment_provider = fields.Nested(FixtureProviderSchema)
    agents = fields.Nested(FixtureProviderSchema, many=True)
    users = fields.Nested(FixtureUserSchema, many=True)


def get_import_agent_kind(agent: BaseAgent) -> ImportAgentKind:
    for agent_type, kind in _import_agent_kind.items():
        if isinstance(agent, agent_type):
            return kind

    click.echo(
        f"The type of import agent {agent.provider_slug} is not currently supported. "
        "Please add an entry into the `_import_agent_kind` dictionary in `harness/run.py` for this agent type."
    )
    raise click.Abort


def payment_card_user_info_fn(fixture: dict) -> t.Callable:
    def payment_card_user_info(loyalty_scheme_slug: str, payment_token: str) -> t.Optional[dict]:
        print(
            "Patched Hermes service responding to payment_card_user_info request "
            f"for {loyalty_scheme_slug}/{payment_token}"
        )

        for idx, user in enumerate(fixture["users"]):
            if user["token"] != payment_token:
                continue

            return {
                payment_token: {
                    "loyalty_id": user["loyalty_id"],
                    "scheme_account_id": idx,
                    "payment_card_account_id": idx,
                    "user_id": idx,
                    "credentials": user["credentials"],
                    "card_information": {
                        "first_six": user["first_six"],
                        "last_four": user["last_four"],
                        "expiry_month": user.get("expiry_month"),
                        "expiry_year": user.get("expiry_year"),
                    },
                }
            }

        for transaction in fixture["payment_provider"].get("transactions", []):
            if transaction["token"] != payment_token:
                continue

            user = fixture["users"][transaction["user_id"]]
            return {
                payment_token: {
                    "loyalty_id": user["loyalty_id"],
                    "scheme_account_id": transaction["user_id"],
                    "user_id": transaction["user_id"],
                    "credentials": user["credentials"],
                    "card_information": {"first_six": user["first_six"], "last_four": user["last_four"]},
                }
            }

        return None

    return payment_card_user_info


def load_fixture(fixture_file: t.IO[str]) -> dict:
    content = toml.load(fixture_file)

    try:
        fixture = FixtureSchema().load(content)
    except ValidationError as ex:
        click.secho("Failed to load fixture", fg="red", bold=True)
        cpprint(ex.messages)
        raise click.Abort
    with mock.patch("app.vault.connect_to_vault", return_value=patch_secret_client()):
        for user in fixture["users"]:
            user["credentials"] = encryption.encrypt_credentials(user["credentials"])
            for transaction in user["transactions"]:
                transaction["settlement_key"] = str(uuid4())

    return fixture


def create_merchant_identifier(fixture: dict, session: db.Session):
    loyalty_scheme, _ = db.get_or_create(models.LoyaltyScheme, session=session, slug=fixture["loyalty_scheme"]["slug"])
    payment_provider, _ = db.get_or_create(
        models.PaymentProvider, session=session, slug=fixture["payment_provider"]["slug"]
    )
    for user in fixture["users"]:
        for transaction in user["transactions"]:
            merchant_identifier = models.MerchantIdentifier(
                identifier=transaction["identifier"],
                identifier_type=transaction["identifier_type"],
                loyalty_scheme_id=loyalty_scheme.id,
                payment_provider_id=payment_provider.id,
                location_id=transaction.get("location_id"),
                location=fixture["location"],
                postcode=fixture["postcode"],
            )
            mid_id = (
                session.query(models.MerchantIdentifier.id)
                .where(
                    models.MerchantIdentifier.identifier == transaction["identifier"],
                    models.MerchantIdentifier.payment_provider_id == payment_provider.id,
                )
                .scalar()
            )
            if mid_id:
                merchant_identifier.id = mid_id
            session.merge(merchant_identifier)
    session.commit()


def preload_import_transactions(count: int, *, fixture: dict, session: db.Session):
    insertions: t.List[t.Dict] = []
    for _ in range(count):
        insertions.append(
            {
                "transaction_id": str(uuid4()),
                "provider_slug": fixture["loyalty_scheme"]["slug"],
                "identified": True,
                "match_group": str(uuid4()),
                "source": "end to end test preload",
                "data": {},
            }
        )

    db.engine.execute(models.ImportTransaction.__table__.insert().values(insertions))


def preload_data(count: int, *, fixture: dict, session: db.Session, batch_size: int = 10000):
    batches = count // batch_size
    remainder = count % batch_size

    click.secho(
        f"Preloading {count} transactions in batches of {batch_size}",
        fg="cyan",
        bold=True,
    )

    with click.progressbar(length=count, label="import transactions") as bar:
        for _ in range(batches):
            preload_import_transactions(batch_size, fixture=fixture, session=session)
            bar.update(batch_size)

        if remainder > 0:
            preload_import_transactions(remainder, fixture=fixture, session=session)
            bar.update(remainder)


def patch_hermes_service(fixture: dict):
    hermes.payment_card_user_info = payment_card_user_info_fn(fixture)


def patch_secret_client():
    class MockSecretClient(SecretClient):
        def get_secret(self, secret_name="abc"):
            mock = MagicMock()
            mock.value = '{"AES_KEY": "fake-123"}'
            return mock

    return MockSecretClient("http://vault", "{}")


def patch_soteria_service():
    class MockSoteriaConfiguration(soteria.configuration.Configuration):
        TRANSACTION_MATCHING = "mock-handler"

        data = {
            "security_credentials": {
                "outbound": {
                    "credentials": [
                        {"credential_type": "compound_key", "value": {"token": "testing token"}},
                        {"credential_type": "merchant_public_key", "value": PGP_PUBLIC_KEY},
                        {"credential_type": "bink_private_key", "value": PGP_PRIVATE_KEY},
                    ],
                    "service": soteria.configuration.Configuration.RSA_SECURITY,
                }
            }
        }
        merchant_url = ""

        def __init__(self, *args, **kwargs):
            click.echo(f"{type(self).__name__} was instantiated!")
            click.echo(f"args: {args}")
            click.echo(f"kwargs: {kwargs}")

        @property
        def security_credentials(self):
            return self.data["security_credentials"]

        def get_security_credentials(self, key_items):
            return self.security_credentials

    def mock_get_security_agent(*args, **kwargs):
        class MockSoteriaAgent:
            def encode(self, body: str) -> dict:
                return {"body": body}

        return MockSoteriaAgent()

    soteria.configuration.Configuration = MockSoteriaConfiguration
    soteria.security.get_security_agent = mock_get_security_agent


ImportDataType = t.Union[bytes, t.List[dict]]


def make_import_data(slug: str, fixture: dict, *, feed_type: feeds.FeedType) -> ImportDataType:
    provider = import_data_providers.instantiate(slug)
    if feed_type == feeds.FeedType.MERCHANT:
        fixture = provider.apply_merchant_overrides(fixture)
    else:
        fixture = provider.apply_payment_provider_overrides(fixture)
    return provider.provide(fixture)


def run_active_api_import_agent(agent_slug: str, agent: ActiveAPIAgent, fixture: dict):
    raise NotImplementedError("Active API import agents are not implemented yet.")


def run_file_import_agent(agent_slug: str, agent: FileAgent, fixture: dict):
    data = t.cast(bytes, make_import_data(agent_slug, fixture, feed_type=agent.feed_type))

    click.secho(
        f"Importing {agent_slug} transaction data",
        fg="cyan",
        bold=True,
    )
    cpprint(data)

    # file agents run as a coroutine
    for _ in agent._do_import(data, "end-to-end test file"):
        pass


def run_queue_import_agent(agent_slug: str, agent: QueueAgent, fixture: dict):
    import_data_list = t.cast(t.List[dict], make_import_data(agent_slug, fixture, feed_type=agent.feed_type))

    click.secho(
        f"Importing {agent_slug} transaction data",
        fg="cyan",
        bold=True,
    )
    for transaction in import_data_list:
        cpprint(transaction)
        agent._do_import(transaction)


def run_import_agent(slug: str, fixture: dict):
    try:
        agent = import_agents.instantiate(slug)
    except NoSuchAgent:
        click.secho(f"No import agent registered for {slug}, skipping", fg="red", bold=True)
        return

    kind = get_import_agent_kind(agent)
    if kind == ImportAgentKind.ACTIVE_API:
        run_active_api_import_agent(slug, t.cast(ActiveAPIAgent, agent), fixture)
    elif kind == ImportAgentKind.FILE:
        run_file_import_agent(slug, t.cast(FileAgent, agent), fixture)
    elif kind == ImportAgentKind.QUEUE:
        run_queue_import_agent(slug, t.cast(QueueAgent, agent), fixture)
    else:
        raise ValueError(f"Unsupported import agent kind: {kind}")


def run_rq_worker(queue_name: str):
    tasks.run_worker([queue_name], burst=True, workerclass=rq.SimpleWorker)


def maybe_run_batch_export_agent(fixture: dict):
    agent = export_agents.instantiate(fixture["loyalty_scheme"]["slug"])
    if not isinstance(agent, BatchExportAgent):
        click.secho(f"Skipping batch export run as {agent} is not a batch export agent.", fg="cyan", bold=True)
        return
    click.secho(f"Running {agent} batch export.", fg="cyan", bold=True)

    with db.session_scope() as session:
        agent.export_all(session=session)


def run_transaction_matching(fixture: dict, *, import_only: bool = False):
    for agent in fixture["agents"]:
        run_import_agent(agent["slug"], fixture)

    if import_only:
        return

    run_rq_worker("identify")
    run_rq_worker("import")
    run_rq_worker("matching")
    run_rq_worker("matching_slow")
    run_rq_worker("streaming")
    run_rq_worker("export")

    # at this point, the event-driven singular exports have already happened.
    # batch export agents will still be waiting their own run.
    maybe_run_batch_export_agent(fixture)


def dump_provider_data(fixture: dict, slug: str):
    provider = import_data_providers.instantiate(slug)
    data = provider.provide(fixture)

    fmt_slug = click.style(slug, fg="cyan", bold=True)

    path = Path("dump") / slug
    path.parent.mkdir(parents=True, exist_ok=True)

    fmt_path = click.style(slug, fg="cyan", bold=True)
    click.echo(f"Dumping {fmt_slug} file to {fmt_path}")
    with path.open("wb") as f:
        if isinstance(data, bytes):
            f.write(data)
        else:
            f.write(json.dumps(data, indent=4, sort_keys=True).encode())


def do_file_dump(fixture: dict):
    for agent in fixture["agents"]:
        dump_provider_data(fixture, agent["slug"])


@click.command()
@click.option(
    "--fixture-file",
    "-f",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, writable=False, readable=True),
    default="harness/fixtures/default.toml",
    show_default=True,
)
@click.option("--dump-files", is_flag=True, help="Dump import files without running end-to-end.")
@click.option("--import-only", is_flag=True, help="Halt after the import step.")
@click.option("--with-prometheus", is_flag=True, help="Run the Prometheus push thread as a daemon.")
@click.option(
    "--preload",
    type=int,
    default=0,
    help="Load the database with this many transactions before running the test.",
    show_default=True,
)
def main(fixture_file: t.IO[str], dump_files: bool, import_only: bool, with_prometheus: bool, preload: int):
    fixture = load_fixture(fixture_file)

    if dump_files:
        do_file_dump(fixture)
        return

    patch_hermes_service(fixture)
    patch_soteria_service()

    with db.session_scope() as session:
        create_merchant_identifier(fixture, session)

        if preload > 0:
            preload_data(preload, fixture=fixture, session=session)

    # Start up the Prometheus http server for serving metrics
    if with_prometheus:
        prometheus_thread.start()

    run_transaction_matching(fixture, import_only=import_only)

    if with_prometheus:
        click.echo("Sleeping for 60 seconds to allow Prometheus push thread to push all stats")
        time.sleep(60)


if __name__ == "__main__":
    main()
