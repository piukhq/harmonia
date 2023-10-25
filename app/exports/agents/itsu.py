import uuid

import pendulum
import sentry_sdk

from app import db, models
from app.config import KEY_PREFIX, Config, ConfigValue
from app.exports.agents.bases.base import AgentExportData, AgentExportDataOutput
from app.exports.agents.bases.singular_export_agent import SingularExportAgent
from app.service import atlas
from app.service.itsu import ItsuApi

PROVIDER_SLUG = "itsu"

BASE_URL_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.base_url"


class Itsu(SingularExportAgent):

    provider_slug = PROVIDER_SLUG

    config = Config(ConfigValue("base_url", key=BASE_URL_KEY, default="http://localhost/"))

    def __init__(self):
        super().__init__()
        self.api_class = ItsuApi

        # Set up Prometheus metric types
        self.prometheus_metrics = {
            "counters": ["requests_sent", "failed_requests", "transactions"],
            "histograms": ["request_latency"],
        }

    @staticmethod
    def get_loyalty_identifier(export_transaction: models.ExportTransaction) -> str:
        return export_transaction.decrypted_credentials["card_number"]

    def make_export_data(self, export_transaction: models.ExportTransaction, session: db.Session) -> AgentExportData:
        dt = pendulum.instance(export_transaction.transaction_date)
        amount = export_transaction.spend_amount / 100
        return AgentExportData(
            outputs=[
                AgentExportDataOutput(
                    "export.json",
                    {
                        "OrderID": str(uuid.uuid4()),
                        "SubTransactions": [
                            {
                                "CustomerDetails": {
                                    "MemberNumber": export_transaction.decrypted_credentials["card_number"],
                                    "ExternalIdentifier": {"ExternalID": "", "ExternalSource": ""},
                                },
                                "TotalAmount": amount,
                                "PaidAmount": amount,
                                "OrderStatusID": 1,
                                "OrderTypeID": 1,
                                "OrderChannelID": 1,
                                "OrderItems": [
                                    {
                                        "ItemID": "1",
                                        "ItemName": "Bink Transaction",
                                        "ItemPrice": amount,
                                    }
                                ],
                            }
                        ],
                        "OrderDate": dt.in_timezone("Europe/London").format("YYYY-MM-DDTHH:mm:ss"),
                        "Location": {"ActeolSiteID": export_transaction.location_id},
                        "Source": "BINK",
                    },
                )
            ],
            transactions=[export_transaction],
            extra_data={"credentials": export_transaction.decrypted_credentials},
        )

    def export(self, export_data: AgentExportData, *, retry_count: int = 0, session: db.Session):
        body: dict
        _, body = export_data.outputs[0]  # type: ignore
        api = self.api_class(self.config.get("base_url", session=session))
        request_timestamp = pendulum.now().to_datetime_string()
        endpoint = "api/Transaction/PostOrder"
        response = api.post_matched_transaction(body, endpoint)

        response_timestamp = pendulum.now().to_datetime_string()

        request_url = api.base_url + endpoint
        atlas.queue_audit_message(
            atlas.make_audit_message(
                self.provider_slug,
                atlas.make_audit_transactions(
                    export_data.transactions, tx_loyalty_ident_callback=self.get_loyalty_identifier
                ),
                request=body,
                request_timestamp=request_timestamp,
                response=response,
                response_timestamp=response_timestamp,
                request_url=request_url,
                retry_count=retry_count,
            )
        )
