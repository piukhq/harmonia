from hashlib import sha256

import pendulum

from app import db, models
from app.config import KEY_PREFIX, Config, ConfigValue
from app.exports.agents.bases.base import AgentExportData, AgentExportDataOutput
from app.exports.agents.bases.singular_export_agent import SingularExportAgent
from app.feeds import FeedType
from app.service import atlas, squaremeal

PROVIDER_SLUG = "squaremeal"

BASE_URL_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.base_url"


class SquareMeal(SingularExportAgent):
    provider_slug = PROVIDER_SLUG
    config = Config(
        ConfigValue("base_url", key=BASE_URL_KEY, default="https://uk-bink-transactions-dev.azurewebsites.net")
    )

    def make_export_data(self, export_transaction: models.ExportTransaction) -> AgentExportData:
        dt = pendulum.instance(export_transaction.transaction_date)

        return AgentExportData(
            outputs=[
                AgentExportDataOutput(
                    "export.json",
                    {
                        "transaction_id": sha256(export_transaction.transaction_id.encode()).hexdigest(),
                        "loyalty_id": export_transaction.loyalty_id,
                        "auth": export_transaction.feed_type == FeedType.AUTH,
                        "cleared": export_transaction.feed_type == FeedType.SETTLED,
                        "mid": export_transaction.mid,
                        "transaction_date": dt.format("YYYY-MM-DDThh:mm:ss"),
                        "transaction_amount": export_transaction.spend_amount,
                        "transaction_currency": "GBP",
                        "payment_card_account_id": export_transaction.payment_card_account_id,
                        "store_id": export_transaction.store_id,
                        "brand_id": export_transaction.brand_id,
                    },
                )
            ],
            transactions=[export_transaction],
            extra_data={},
        )

    def export(
        self, export_data: AgentExportData, *, retry_count: int = 0, session: db.Session
    ) -> atlas.MessagePayload:
        body: dict
        _, body = export_data.outputs[0]  # type: ignore

        api = squaremeal.SquareMeal(self.config.get("base_url", session))

        request_timestamp = pendulum.now().to_datetime_string()
        response = api.transactions(body)
        response_timestamp = pendulum.now().to_datetime_string()

        audit_message = atlas.make_audit_message(
            self.provider_slug,
            atlas.make_audit_transactions(export_data.transactions, tx_loyalty_ident_callback=lambda tx: tx.loyalty_id),
            request=body,
            request_timestamp=request_timestamp,
            response=response,
            response_timestamp=response_timestamp,
        )
        return audit_message
