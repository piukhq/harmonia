import csv
import io
from collections.abc import Iterable

import pendulum

from app import db, models
from app.config import KEY_PREFIX, Config, ConfigValue
from app.exports.agents import AgentExportData, AgentExportDataOutput, BatchExportAgent
from app.sequences import batch
from app.service import atlas

PROVIDER_SLUG = "stonegate-unmatched"
SCHEDULE_KEY = f"{KEY_PREFIX}agents.exports.{PROVIDER_SLUG}.schedule"
BATCH_SIZE_KEY = f"{KEY_PREFIX}agents.exports.{PROVIDER_SLUG}.batch_size"


class StonegateUnmatched(BatchExportAgent):
    provider_slug = PROVIDER_SLUG

    config = Config(
        ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *"),
        ConfigValue("batch_size", key=BATCH_SIZE_KEY, default="1000"),
    )

    def __init__(self):
        super().__init__()

        # Set up Prometheus metric types
        self.prometheus_metrics = {
            "counters": ["requests_sent", "failed_requests", "transactions"],
            "histograms": ["request_latency"],
        }

    @staticmethod
    def get_loyalty_identifier(export_transaction: models.ExportTransaction) -> str:
        return export_transaction.loyalty_id

    def csv_transactions(self, transactions: list[models.ExportTransaction]) -> str:
        # transaction_id,member_number,retailer_location_id,transaction_amount,transaction_date
        export_transactions = [
            (
                transaction.transaction_id,
                transaction.loyalty_id,
                transaction.location_id,
                transaction.spend_amount,
                transaction.transaction_date,
            )
            for transaction in transactions
        ]
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            (
                "transaction_id",
                "member_number",
                "retailer_location_id",
                "transaction_amount",
                "transaction_date",
            )
        )
        writer.writerows(export_transactions)
        return buf.getvalue()

    def yield_export_data(
        self, transactions: list[models.MatchedTransaction], *, session: db.Session
    ) -> Iterable[AgentExportData]:
        batch_size = int(self.config.get("batch_size", session=session))
        for i, transaction_set in enumerate(batch(transactions, size=batch_size)):
            yield self._make_export_data(transaction_set)

    def _make_export_data(self, transactions: list[models.ExportTransaction]) -> AgentExportData:
        csv_transactions = self.csv_transactions(transactions)
        date = pendulum.now().format("YYYYMMDDTHHmmss")
        num_transactions = len(transactions)
        return AgentExportData(
            outputs=[
                AgentExportDataOutput(
                    f"stonegate_date{date}_rows{num_transactions}_data.csv",
                    csv_transactions,
                )
            ],
            transactions=transactions,
            extra_data={},
        )

    def send_export_data(self, export_data: AgentExportData, *, session: db.Session) -> atlas.MessagePayload:
        blob_names = self.save_to_blob("harmonia-exports", export_data)
        audit_message = atlas.make_audit_message(
            self.provider_slug,
            atlas.make_audit_transactions(
                export_data.transactions,
                tx_loyalty_ident_callback=self.get_loyalty_identifier,
            ),
            blob_names=blob_names,
        )
        return audit_message
