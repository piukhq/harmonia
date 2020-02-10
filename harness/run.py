import typing as t
from datetime import datetime
from enum import Enum

import click
import toml
from flask import Flask
from marshmallow import ValidationError, fields
from marshmallow.schema import Schema
from prettyprinter import cpprint

import settings
from app import db, models
from app.imports.agents.bases.active_api_agent import ActiveAPIAgent
from app.imports.agents.bases.file_agent import FileAgent
from app.imports.agents.bases.passive_api_agent import PassiveAPIAgent
from app.service.hermes import hermes
from harness.providers.registry import import_data_providers


class IdentityDateTimeField(fields.DateTime):
    def _deserialize(self, value, attr, data, **kwargs):
        if isinstance(value, datetime):
            return value
        return super()._deserialize(value, attr, data, **kwargs)


class FixtureProviderSchema(Schema):
    slug = fields.String(required=True, allow_none=False)


class FixtureUserTransactionSchema(Schema):
    date = IdentityDateTimeField(required=True, allow_none=False)
    amount = fields.Integer(required=True, allow_none=False, strict=True)
    points = fields.Integer(required=True, allow_none=False, strict=True)


class FixtureUserSchema(Schema):
    token = fields.String(required=True, allow_none=False)
    loyalty_id = fields.String(required=True, allow_none=False)
    credentials = fields.Dict(required=True, allow_none=False)
    transactions = fields.Nested(FixtureUserTransactionSchema, many=True)


class FixtureSchema(Schema):
    mid = fields.String(required=True, allow_none=False)
    location = fields.String(required=True, allow_none=False)
    postcode = fields.String(required=True, allow_none=False)
    loyalty_scheme = fields.Nested(FixtureProviderSchema)
    payment_provider = fields.Nested(FixtureProviderSchema)
    users = fields.Nested(FixtureUserSchema, many=True)


class ImportAgentKind(Enum):
    PASSIVE_API = "Passive API"
    ACTIVE_API = "Active API"
    FILE = "File"


_import_agent_kind = {
    "bink-loyalty": ImportAgentKind.PASSIVE_API,
    "bink-payment": ImportAgentKind.PASSIVE_API,
}


def get_import_agent_kind(slug: str) -> ImportAgentKind:
    try:
        return _import_agent_kind[slug]
    except KeyError:
        click.echo(
            f"Import agent {slug} is not currently supported. "
            "Please add an entry into the `_import_agent_kind` dictionary in `harness/run.py` for this agent."
        )


def payment_card_user_info_fn(fixture: dict) -> t.Callable:
    def payment_card_user_info(loyalty_scheme_slug: str, payment_token: str) -> dict:
        print(
            "Patched Hermes service responding to payment_card_user_info request "
            f"for {loyalty_scheme_slug}/{payment_token}"
        )

        for idx, user in enumerate(fixture["users"]):
            if user["token"] != payment_token:
                continue
            """
            loyalty_id=user_info["loyalty_id"],
            scheme_account_id=user_info["scheme_account_id"],
            user_id=user_info["user_id"],
            credentials=user_info["credentials"],
            """
            return {
                payment_token: {
                    "loyalty_id": user["loyalty_id"],
                    "scheme_account_id": idx,
                    "user_id": idx,
                    "credentials": "",
                }
            }

    return payment_card_user_info


def load_fixture(fixture_file: t.IO[str]) -> dict:
    fixture = toml.load(fixture_file)

    try:
        return FixtureSchema().load(fixture)
    except ValidationError as ex:
        click.secho("Failed to load fixture", fg="red", bold=True)
        cpprint(ex.messages)
        raise click.Abort


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
            click.secho("Success", fg="green", bold=True)
        else:
            click.echo(resp.status)
            cpprint(resp.json)
            click.secho("Failed", fg="red", bold=True)


def run_active_api_import_agent(agent: ActiveAPIAgent, fixture: dict):
    raise NotImplementedError()


def run_file_import_agent(agent: FileAgent, fixture: dict):
    raise NotImplementedError()


def run_import_agent(slug: str, fixture: dict):
    from app.imports.agents.registry import import_agents

    kind = get_import_agent_kind(slug)
    agent = import_agents.instantiate(slug)

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
    click.secho("Success", fg="green", bold=True)


def run_transaction_matching(fixture: dict):
    loyalty_scheme_slug = fixture["loyalty_scheme"]["slug"]
    payment_provider_slug = fixture["payment_provider"]["slug"]

    run_import_agent(loyalty_scheme_slug, fixture)
    run_import_agent(payment_provider_slug, fixture)
    run_rq_worker("import")
    run_rq_worker("matching")


@click.command()
@click.option(
    "--fixture-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, writable=False, readable=True),
    default="harness/fixtures/default.toml",
    show_default=True,
)
def main(fixture_file: t.IO[str]):
    fixture = load_fixture(fixture_file)
    patch_hermes_service(fixture)
    create_merchant_identifier(fixture)
    run_transaction_matching(fixture)


if __name__ == "__main__":
    main()
