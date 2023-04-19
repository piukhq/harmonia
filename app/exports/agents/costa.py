from hashlib import sha256

import pendulum

from app import db, models
from app.config import KEY_PREFIX, Config, ConfigValue
from app.exports.agents.bases.base import AgentExportData, AgentExportDataOutput
from app.exports.agents.bases.singular_export_agent import SingularExportAgent
from app.service import atlas, costa

PROVIDER_SLUG = "costa"

BASE_URL_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.base_url"


class Costa(SingularExportAgent):
    provider_slug = PROVIDER_SLUG
    config = Config(
        ConfigValue("base_url", key=BASE_URL_KEY, default="https://reflector.staging.gb.bink.com/mock/")
    )

    def make_export_data(self, export_transaction: models.ExportTransaction, session: db.Session) -> AgentExportData:
        dt = pendulum.instance(export_transaction.transaction_date)

        return AgentExportData(
            outputs=[
                AgentExportDataOutput(
                    "export.json",
                    {
                        "loyalty_id": export_transaction.loyalty_id,
                        "ExternalCustomerID": "????????????????"
                    },
                )
            ],
            transactions=[export_transaction],
            extra_data={},
        )

    def export(self, export_data: AgentExportData, *, retry_count: int = 0, session: db.Session) -> None:
        body: dict
        _, body = export_data.outputs[0]  # type: ignore

        api = costa.Costa(self.config.get("base_url", session))
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
