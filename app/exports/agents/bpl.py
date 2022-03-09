from hashlib import sha1

import pendulum

from app import db, models
from app.config import KEY_PREFIX, Config, ConfigValue
from app.exports.agents.bases.base import AgentExportData, AgentExportDataOutput
from app.exports.agents.bases.singular_export_agent import SingularExportAgent
from app.service import atlas
from app.service.bpl import BplAPI


class Bpl(SingularExportAgent):
    def __init__(self, merchant_name: str):
        super().__init__()
        self.api_class = BplAPI
        self.merchant_name = merchant_name
        base_url_key = f"{KEY_PREFIX}exports.agents.{self.provider_slug}.base_url"
        self.config = Config(ConfigValue("base_url", key=base_url_key, default="http://localhost"))

    @staticmethod
    def get_loyalty_identifier(export_transaction: models.ExportTransaction) -> str:
        return export_transaction.decrypted_credentials["merchant_identifier"]

    def make_export_data(self, export_transaction: models.ExportTransaction) -> AgentExportData:
        transaction_datetime = pendulum.instance(export_transaction.transaction_date)

        return AgentExportData(
            outputs=[
                AgentExportDataOutput(
                    "export.json",
                    {
                        "id": f"BPL{sha1(export_transaction.transaction_id.encode()).hexdigest()}",
                        "transaction_total": export_transaction.spend_amount,
                        "datetime": transaction_datetime.int_timestamp,
                        "MID": export_transaction.mid,
                        "loyalty_id": self.get_loyalty_identifier(export_transaction),
                    },
                )
            ],
            transactions=[export_transaction],
            extra_data={},
        )

    def export(self, export_data: AgentExportData, *, retry_count: int = 0, session: db.Session) -> None:
        body: dict
        _, body = export_data.outputs[0]  # type: ignore
        api = self.api_class(self.config.get("base_url", session=session), self.provider_slug)
        request_timestamp = pendulum.now().to_datetime_string()
        response = api.post_matched_transaction(self.merchant_name, body)
        response_timestamp = pendulum.now().to_datetime_string()

        if (300 <= response.status_code <= 399) or (response.status_code >= 500):
            raise Exception(f"BPL - {self.provider_slug} transaction endpoint returned {response.status_code}")

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
            )
        )


class Trenette(Bpl):
    provider_slug = "bpl-trenette"

    def __init__(self, merchant_name="trenette"):
        super().__init__()


class Asos(Bpl):
    provider_slug = "bpl-asos"

    def __init__(self, merchant_name="asos"):
        super().__init__()
