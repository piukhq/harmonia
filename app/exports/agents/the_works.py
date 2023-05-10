import json

import pendulum

from app import db, models
from app.config import KEY_PREFIX, Config, ConfigValue
from app.exports.agents.bases.base import AgentExportData, AgentExportDataOutput
from app.exports.agents.bases.singular_export_agent import SingularExportAgent
from app.service import atlas, the_works

PROVIDER_SLUG = "the-works"

BASE_URL_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.base_url"


class TheWorks(SingularExportAgent):
    provider_slug = PROVIDER_SLUG
    config = Config(ConfigValue("base_url", key=BASE_URL_KEY, default="https://reflector.staging.gb.bink.com/mock/"))

    def make_export_data(self, export_transaction: models.ExportTransaction, session: db.Session) -> AgentExportData:
        metadata = {}
        if export_transaction.extra_fields:
            extra_fields = json.loads(export_transaction.extra_fields)
            if extra_fields and extra_fields["metadata"]:
                metadata = extra_fields["metadata"]

        return AgentExportData(
            outputs=[
                AgentExportDataOutput(
                    "export.json",
                    {
                        "payload": metadata,
                        "ExternalCustomerID": export_transaction.loyalty_id,
                    },
                )
            ],
            transactions=[export_transaction],
            extra_data=export_transaction.extra_fields,
        )

    def export(self, export_data: AgentExportData, *, retry_count: int = 0, session: db.Session) -> None:
        body: dict
        _, body = export_data.outputs[0]  # type: ignore

        # The Works export transaction process requires a check against known rewarded transactions
        # This means we need to request a transaction history from The Works, the compare
        # the current transaction with the works transactions.
        api = the_works.TheWorksAPI(self.config.get("base_url", session))
        endpoint = "/costa/transactions"
        request_timestamp = pendulum.now().to_datetime_string()
        response = api.transactions(body, endpoint)
        response_timestamp = pendulum.now().to_datetime_string()

        request_url = api.base_url + endpoint
        atlas.queue_audit_message(
            atlas.make_audit_message(
                self.provider_slug,
                atlas.make_audit_transactions(
                    export_data.transactions, tx_loyalty_ident_callback=lambda tx: tx.loyalty_id
                ),
                request=body,
                request_timestamp=request_timestamp,
                response=response,
                response_timestamp=response_timestamp,
                request_url=request_url,
                retry_count=retry_count,
            )
        )
