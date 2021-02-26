from decimal import Decimal

from app import db, models
from app.exports.agents import SingularExportAgent, AgentExportData, AgentExportDataOutput


class BinkLoyalty(SingularExportAgent):
    provider_slug = "bink-loyalty"

    def make_export_data(self, matched_transaction: models.MatchedTransaction) -> AgentExportData:
        value = Decimal(matched_transaction.spend_amount) / Decimal(matched_transaction.spend_multiplier)
        body = {
            "tid": matched_transaction.transaction_id,
            "value": f"{matched_transaction.spend_currency} {value.quantize(Decimal('0.01'))}",
            "card_number": matched_transaction.payment_transaction.user_identity.loyalty_id,
        }
        return AgentExportData(
            outputs=[AgentExportDataOutput("export.json", body)], transactions=[matched_transaction], extra_data={}
        )

    def export(self, export_data: AgentExportData, *, retry_count: int = 0, session: db.Session):
        _, body = export_data.outputs[0]
        self.log.info(f"Export: {body}")
