from hashlib import sha256

import pendulum

from app import db, models
from app.config import KEY_PREFIX, Config, ConfigValue
from app.exports.agents.bases.base import AgentExportData, AgentExportDataOutput
from app.exports.agents.bases.singular_export_agent import SingularExportAgent
from app.exports.exceptions import MissingExportData
from app.feeds import FeedType
from app.service import atlas, squaremeal

PROVIDER_SLUG = "squaremeal"

BASE_URL_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.base_url"


class SquareMeal(SingularExportAgent):
    provider_slug = PROVIDER_SLUG
    config = Config(
        ConfigValue("base_url", key=BASE_URL_KEY, default="https://uk-bink-transactions-dev.azurewebsites.net")
    )

    def get_settlement_key(self, export_transaction: models.ExportTransaction, session: db.Session) -> str:
        # Check if there is a settlement key since a transaction might already be in the export queue
        # If no settlement key, then obtain it from the transaction table data
        if settlement_key := export_transaction.settlement_key:
            return settlement_key
        else:
            settlement_key = db.run_query(
                session.query(models.Transaction.settlement_key)
                .filter(
                    models.Transaction.feed_type == export_transaction.feed_type,
                    models.Transaction.transaction_id == export_transaction.transaction_id,
                )
                .scalar,
                session=session,
                read_only=True,
                description="find transaction settlement key for export",
            )
        self.log.warning(f"Settlement key not found for SquareMeal transaction: {export_transaction}")
        return settlement_key

    @staticmethod
    def _export_transaction_is_valid(export_transaction: models.ExportTransaction) -> bool:
        if not export_transaction.location_id or not export_transaction.merchant_internal_id:
            return False
        return True

    def make_export_data(self, export_transaction: models.ExportTransaction, session: db.Session) -> AgentExportData:
        dt = pendulum.instance(export_transaction.transaction_date)

        # Squaremeal requires that certain data is available in the export transaction
        if not self._export_transaction_is_valid(export_transaction):
            raise MissingExportData

        return AgentExportData(
            outputs=[
                AgentExportDataOutput(
                    "export.json",
                    {
                        "transaction_id": sha256(
                            self.get_settlement_key(export_transaction, session).encode()
                        ).hexdigest(),
                        "loyalty_id": export_transaction.loyalty_id,
                        "auth": export_transaction.feed_type == FeedType.AUTH,
                        "cleared": export_transaction.feed_type in (FeedType.SETTLED, FeedType.REFUND),
                        "mid": export_transaction.mid,
                        "transaction_date": dt.in_timezone("Europe/London").format("YYYY-MM-DDTHH:mm:ss"),
                        "transaction_amount": export_transaction.spend_amount,
                        "transaction_currency": "GBP",
                        "payment_card_account_id": export_transaction.payment_card_account_id,
                        "store_id": export_transaction.location_id,
                        "brand_id": export_transaction.merchant_internal_id,
                        "payment_card_last_four": export_transaction.last_four,
                        "payment_scheme": {
                            "slug": export_transaction.payment_provider_slug,
                            "auth_code": export_transaction.auth_code,
                            "approval_code": export_transaction.approval_code,
                        },
                        "payment_card_expiry_month": export_transaction.expiry_month,
                        "payment_card_expiry_year": export_transaction.expiry_year,
                    },
                )
            ],
            transactions=[export_transaction],
            extra_data={},
        )

    def export(self, export_data: AgentExportData, *, retry_count: int = 0, session: db.Session) -> None:
        body: dict
        _, body = export_data.outputs[0]  # type: ignore

        api = squaremeal.SquareMeal(self.config.get("base_url", session))
        endpoint = "/api/BinkTransactions"
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
            )
        )
