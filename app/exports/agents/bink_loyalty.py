from decimal import Decimal

from app.exports.agents.bases.single_export_agent import SingleExportAgent
from app.exports.agents.bases.base import AgentExportData
from app import models, db


class BinkLoyalty(SingleExportAgent):
    provider_slug = "bink-loyalty"

    def make_export_data(self, matched_transaction_id):
        matched_transaction = db.session.query(models.MatchedTransaction).get(matched_transaction_id)

        if matched_transaction is None:
            self.log.warning(
                f"Failed to load matched transaction #{matched_transaction_id} - record may have been deleted."
            )
            raise db.NoResultFound

        self.log.info(f"{type(self).__name__} handling {matched_transaction}.")

        value = Decimal(matched_transaction.spend_amount) / Decimal(matched_transaction.spend_multiplier)
        body = {
            "tid": matched_transaction.transaction_id,
            "value": f"{matched_transaction.spend_currency} {value.quantize(Decimal('0.01'))}",
            "card_number": matched_transaction.payment_transaction.user_identity.loyalty_id,
        }
        return AgentExportData(body=body, transactions=[matched_transaction])

    def export(self, export_data: AgentExportData) -> bool:
        body = export_data.body
        matched_transaction = export_data.transactions[0]

        self.log.info(f"Export: {body}")

        self.log.info(f"Marking {matched_transaction} as exported.")
        matched_transaction.status = models.MatchedTransactionStatus.EXPORTED

        self.log.info("Creating export transaction.")

        def add_transaction():
            db.session.add(
                models.ExportTransaction(
                    matched_transaction_id=matched_transaction.id,
                    transaction_id=matched_transaction.transaction_id,
                    provider_slug=self.provider_slug,
                    destination="the great unknown",
                    data=export_data,
                )
            )

            db.session.commit()

        db.run_query(add_transaction, description="create export transaction")

        return True
