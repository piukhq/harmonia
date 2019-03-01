import inspect
from decimal import Decimal

from app.db import session
from app.exports.agents.bases.single_export_agent import SingleExportAgent
from app.models import ExportTransaction, MatchedTransaction, MatchedTransactionStatus


class ExampleLoyaltySchemeAgent(SingleExportAgent):
    provider_slug = "example-loyalty-scheme"

    def help(self):
        return inspect.cleandoc(
            f"""
            This agent exports {self.provider_slug} transactions.
            """
        )

    def export(self, matched_transaction_id: int, *, once: bool = False):
        matched_transaction = session.query(MatchedTransaction).get(matched_transaction_id)
        self.log.info(f"{type(self).__name__} handling {matched_transaction}.")

        value = Decimal(matched_transaction.spend_amount) / Decimal(matched_transaction.spend_multiplier)
        export_data = {
            "transaction_id": matched_transaction.transaction_id,
            "value": f"{matched_transaction.spend_currency} {value.quantize(Decimal('0.01'))}",
            "loyalty_card_number": matched_transaction.user_identity.loyalty_id,
        }
        self.log.info(f"In a real agent we'd send this somewhere: {export_data}")

        self.log.info(f"Marking {matched_transaction} as exported.")
        matched_transaction.status = MatchedTransactionStatus.EXPORTED

        self.log.info("Creating export transaction.")

        session.add(
            ExportTransaction(
                matched_transaction_id=matched_transaction.id,
                transaction_id=matched_transaction.transaction_id,
                provider_slug=self.provider_slug,
                destination="nowhere",
                data=export_data,
            )
        )

        session.commit()

        return True
