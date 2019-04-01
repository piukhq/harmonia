from decimal import Decimal

from app.exports.agents.bases.single_export_agent import SingleExportAgent
from app import models, db


class BinkLoyalty(SingleExportAgent):
    provider_slug = "bink-loyalty"

    def export(self, matched_transaction_id: int):
        matched_transaction = db.session.query(models.MatchedTransaction).get(matched_transaction_id)
        self.log.info(f"{type(self).__name__} handling {matched_transaction}.")

        value = Decimal(matched_transaction.spend_amount) / Decimal(matched_transaction.spend_multiplier)
        export_data = {
            "tid": matched_transaction.transaction_id,
            "value": f"{matched_transaction.spend_currency} {value.quantize(Decimal('0.01'))}",
            "card_number": matched_transaction.user_identity.loyalty_id,
        }
        self.log.info(f"Export: {export_data}")

        self.log.info(f"Marking {matched_transaction} as exported.")
        matched_transaction.status = models.MatchedTransactionStatus.EXPORTED

        self.log.info("Creating export transaction.")

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

        return True
