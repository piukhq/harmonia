from hashlib import sha1

import pendulum

from app import db, models
from app.config import KEY_PREFIX, Config, ConfigValue
from app.exports.agents.bases.base import AgentExportData, AgentExportDataOutput
from app.exports.agents.bases.singular_export_agent import SingularExportAgent
from app.service import atlas
from app.service.bpl import BplAPI
from app.utils import missing_property


class Bpl(SingularExportAgent):
    def __init__(self):
        super().__init__()
        self.api_class = BplAPI
        base_url_key = f"{KEY_PREFIX}exports.agents.{self.provider_slug}.base_url"
        self.config = Config(ConfigValue("base_url", key=base_url_key, default="http://localhost"))

    @property
    def merchant_name(self) -> str:
        return missing_property(type(self), "merchant_name")

    @staticmethod
    def get_loyalty_identifier(export_transaction: models.ExportTransaction) -> str:
        return export_transaction.decrypted_credentials["merchant_identifier"]

    def export_transaction_id(self, export_transaction: models.ExportTransaction, transaction_datetime: int) -> str:
        transaction_id = (
            f"{export_transaction.transaction_id}-refund"
            if export_transaction.spend_amount < 0
            else export_transaction.transaction_id
        )

        return self.provider_slug + "-" + sha1((transaction_id + str(transaction_datetime)).encode()).hexdigest()

    def make_export_data(self, export_transaction: models.ExportTransaction, session: db.Session) -> AgentExportData:
        transaction_datetime = pendulum.instance(export_transaction.transaction_date).int_timestamp

        return AgentExportData(
            outputs=[
                AgentExportDataOutput(
                    "export.json",
                    {
                        "id": self.export_transaction_id(export_transaction, transaction_datetime),
                        "transaction_total": export_transaction.spend_amount,
                        "datetime": transaction_datetime,
                        "MID": export_transaction.primary_identifier,
                        "loyalty_id": self.get_loyalty_identifier(export_transaction),
                        "transaction_id": export_transaction.transaction_id,
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
        endpoint = f"/{self.merchant_name}/transaction"
        response = api.post_matched_transaction(body, endpoint)
        response_timestamp = pendulum.now().to_datetime_string()

        if (300 <= response.status_code <= 399) or (response.status_code >= 500):
            raise Exception(f"BPL - {self.provider_slug} transaction endpoint returned {response.status_code}")

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
            )
        )


class Trenette(Bpl):
    provider_slug = "bpl-trenette"
    merchant_name = "trenette"


class Asos(Bpl):
    provider_slug = "bpl-asos"
    merchant_name = "asos"


class Viator(Bpl):
    provider_slug = "bpl-viator"
    merchant_name = "viator"


class Cortado(Bpl):
    provider_slug = "bpl-cortado"
    merchant_name = "cortado"
