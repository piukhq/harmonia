import shutil
import typing as t
from datetime import datetime
from enum import Enum
from pathlib import Path

import gnupg
import click
import toml
from flask import Flask
from marshmallow import ValidationError, fields, validate
from marshmallow.schema import Schema
from prettyprinter import cpprint

import settings
from app import db, models, encryption
from app.core import key_manager
from app.imports.agents import BaseAgent, ActiveAPIAgent, PassiveAPIAgent, FileAgent
from app.service.hermes import hermes
from harness.providers.registry import import_data_providers


# payment provider slugs that will trigger a keyring being set up
KEYRING_REQUIRED = ["visa"]


class ImportAgentKind(Enum):
    PASSIVE_API = "Passive API"
    ACTIVE_API = "Active API"
    FILE = "File"


_import_agent_kind = {
    PassiveAPIAgent: ImportAgentKind.PASSIVE_API,
    ActiveAPIAgent: ImportAgentKind.ACTIVE_API,
    FileAgent: ImportAgentKind.FILE,
}


class IdentityDateTimeField(fields.DateTime):
    def _deserialize(self, value, attr, data, **kwargs):
        if isinstance(value, datetime):
            return value
        return super()._deserialize(value, attr, data, **kwargs)


class FixtureProviderSchema(Schema):
    slug = fields.String(required=True, allow_none=False, validate=validate.Length(min=1))


class FixtureUserTransactionSchema(Schema):
    date = IdentityDateTimeField(required=True, allow_none=False)
    amount = fields.Integer(required=True, allow_none=False, strict=True)
    points = fields.Integer(required=True, allow_none=False, strict=True)


class FixtureUserSchema(Schema):
    token = fields.String(required=True, allow_none=False, validate=validate.Length(min=1))
    loyalty_id = fields.String(required=True, allow_none=False, validate=validate.Length(min=1))
    first_six = fields.String(required=True, allow_none=False, validate=validate.Length(equal=6))
    last_four = fields.String(required=True, allow_none=False, validate=validate.Length(equal=4))
    credentials = fields.Dict(required=True, allow_none=False)
    transactions = fields.Nested(FixtureUserTransactionSchema, many=True)


class FixtureSchema(Schema):
    mid = fields.String(required=True, allow_none=False)
    location = fields.String(required=True, allow_none=False)
    postcode = fields.String(required=True, allow_none=False)
    loyalty_scheme = fields.Nested(FixtureProviderSchema)
    payment_provider = fields.Nested(FixtureProviderSchema)
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
    def payment_card_user_info(loyalty_scheme_slug: str, payment_token: str) -> dict:
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
                    "user_id": idx,
                    "credentials": user["credentials"],
                    "card_information": {"first_six": user["first_six"], "last_four": user["last_four"]},
                }
            }

    return payment_card_user_info


def load_fixture(fixture_file: t.IO[str]) -> dict:
    content = toml.load(fixture_file)

    try:
        fixture = FixtureSchema().load(content)
    except ValidationError as ex:
        click.secho("Failed to load fixture", fg="red", bold=True)
        cpprint(ex.messages)
        raise click.Abort

    for user in fixture["users"]:
        user["credentials"] = encryption.encrypt_credentials(user["credentials"])

    return fixture


def create_merchant_identifier(fixture: dict):
    loyalty_scheme, _ = db.get_or_create(models.LoyaltyScheme, slug=fixture["loyalty_scheme"]["slug"])
    payment_provider, _ = db.get_or_create(models.PaymentProvider, slug=fixture["payment_provider"]["slug"])
    db.get_or_create(
        models.MerchantIdentifier,
        mid=fixture["mid"],
        loyalty_scheme=loyalty_scheme,
        payment_provider=payment_provider,
        location=fixture["location"],
        postcode=fixture["postcode"],
    )


def patch_hermes_service(fixture: dict):
    hermes.payment_card_user_info = payment_card_user_info_fn(fixture)


def setup_keyring():
    gpg_home = Path(settings.GPG_ARGS["gnupghome"])
    if gpg_home.exists():
        shutil.rmtree(gpg_home)
    gpg_home.mkdir(parents=True)

    gpg = gnupg.GPG(**settings.GPG_ARGS)
    input_data = gpg.gen_key_input(name_email="harmonia@bink.dev")
    key = gpg.gen_key(input_data)
    priv_key_data = gpg.export_keys(key.fingerprint, secret=True, armor=False)
    manager = key_manager.KeyManager()
    manager.write_key("visa", priv_key_data)


def make_import_data(slug: str, fixture: dict) -> dict:
    provider = import_data_providers.instantiate(slug)
    return provider.provide(fixture)


def make_test_client(agent: PassiveAPIAgent):
    bp = agent.get_blueprint()
    app = Flask(__name__)
    app.register_blueprint(bp)
    return app.test_client()


def run_passive_api_import_agent(agent: PassiveAPIAgent, fixture: dict):
    import_data_list = make_import_data(agent.provider_slug, fixture)
    client = make_test_client(agent)
    url = f"{settings.URL_PREFIX}/import/{agent.provider_slug}/"

    for import_data in import_data_list:
        click.secho(
            f"Importing {agent.provider_slug} transaction #{agent.get_transaction_id(import_data)}",
            fg="cyan",
            bold=True,
        )
        click.echo(f"POST {url}")
        cpprint(import_data)
        resp = client.post(url, json=import_data)

        if 200 <= resp.status_code <= 299:
            cpprint(resp.json)
        else:
            click.echo(resp.status)
            cpprint(resp.json)
            click.secho("Failed", fg="red", bold=True)


def run_active_api_import_agent(agent: ActiveAPIAgent, fixture: dict):
    raise NotImplementedError("Active API import agents are not implemented yet.")


def run_file_import_agent(agent: FileAgent, fixture: dict):
    provider = import_data_providers.instantiate(agent.provider_slug)
    data = provider.provide(fixture)
    click.secho(
        f"Importing {agent.provider_slug} transaction data", fg="cyan", bold=True,
    )
    agent._do_import(data, "end-to-end test file")


def run_import_agent(slug: str, fixture: dict):
    from app.imports.agents.registry import import_agents

    agent = import_agents.instantiate(slug)
    kind = get_import_agent_kind(agent)

    return {
        ImportAgentKind.PASSIVE_API: run_passive_api_import_agent,
        ImportAgentKind.ACTIVE_API: run_active_api_import_agent,
        ImportAgentKind.FILE: run_file_import_agent,
    }[kind](agent, fixture)


def run_rq_worker(queue_name: str):
    from rq import Queue, Worker
    from redis import Redis
    import rq_worker_settings as config

    redis = Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB, password=config.REDIS_PASSWORD)
    queue = Queue(queue_name, connection=redis)
    worker = Worker([queue], connection=redis, name="end-to-end test matching worker")

    click.secho(f"Running {queue_name} worker", fg="cyan", bold=True)
    worker.work(burst=True, logging_level="WARNING")


def run_transaction_matching(fixture: dict):
    loyalty_scheme_slug = fixture["loyalty_scheme"]["slug"]
    payment_provider_slug = fixture["payment_provider"]["slug"]

    run_import_agent(loyalty_scheme_slug, fixture)
    run_import_agent(payment_provider_slug, fixture)
    run_rq_worker("import")
    run_rq_worker("matching")


def dump_provider_data(fixture: dict, slug: str):
    provider = import_data_providers.instantiate(slug)
    data = provider.provide(fixture)

    fmt_slug = click.style(slug, fg="cyan", bold=True)

    if not isinstance(data, bytes):
        click.echo(f"Skipping {fmt_slug} as provided data was not bytes")
        return

    path = Path("dump") / slug
    path.parent.mkdir(parents=True, exist_ok=True)

    fmt_path = click.style(slug, fg="cyan", bold=True)
    click.echo(f"Dumping {fmt_slug} file to {fmt_path}")
    with path.open("wb") as f:
        f.write(data)


def do_file_dump(fixture: dict):
    dump_provider_data(fixture, fixture["loyalty_scheme"]["slug"])
    dump_provider_data(fixture, fixture["payment_provider"]["slug"])


@click.command()
@click.option(
    "--fixture-file",
    "-f",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, writable=False, readable=True),
    default="harness/fixtures/default.toml",
    show_default=True,
)
@click.option("--dump-files", is_flag=True, help="Dump import files without running end-to-end.")
def main(fixture_file: t.IO[str], dump_files: bool):
    fixture = load_fixture(fixture_file)

    if fixture["payment_provider"]["slug"] in KEYRING_REQUIRED:
        setup_keyring()

    if dump_files:
        do_file_dump(fixture)
        return

    patch_hermes_service(fixture)
    create_merchant_identifier(fixture)
    run_transaction_matching(fixture)


if __name__ == "__main__":
    main()
