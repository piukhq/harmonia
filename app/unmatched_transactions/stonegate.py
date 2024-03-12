import pendulum

from app import db, models
from app.config import KEY_PREFIX, Config, ConfigValue
from app.feeds import FeedType
from app.models import TransactionStatus
from app.unmatched_transactions.base import BaseAgent

PROVIDER_SLUG = "stonegate_unmatched"
SCHEDULE_KEY = f"{KEY_PREFIX}agents.unmatched_transactions.{PROVIDER_SLUG}.schedule"


class Stonegate(BaseAgent):
    provider_slug = PROVIDER_SLUG

    config = Config(
        ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *"),
    )

    def __init__(self):
        super().__init__()

    def find_unmatched_transactions(self, session: db.Session) -> list[int]:
        unmatched_transaction_ids = []

        visa_unmatched_transaction_ids = (
            session.query(models.Transaction.id)
            .join(
                models.PaymentTransaction,
                models.Transaction.transaction_id == models.PaymentTransaction.transaction_id,
            )
            .filter(
                models.PaymentTransaction.status == TransactionStatus.PENDING.name,
                models.Transaction.merchant_slug == self.provider_slug,
                models.Transaction.payment_provider_slug == "visa",
                models.Transaction.feed_type != FeedType.REFUND.name,
                models.Transaction.transaction_date < pendulum.now().date().subtract(days=2),
            )
            .all()
        )

        for id_tuple in visa_unmatched_transaction_ids:
            unmatched_transaction_ids.append(id_tuple[0])

        mastercard_and_amex_unmatched_transaction_ids = (
            session.query(models.Transaction.id)
            .join(
                models.PaymentTransaction,
                models.Transaction.transaction_id == models.PaymentTransaction.transaction_id,
            )
            .filter(
                models.PaymentTransaction.status == TransactionStatus.PENDING.name,
                models.Transaction.merchant_slug == self.provider_slug,
                models.Transaction.feed_type == FeedType.SETTLED.name,
                models.Transaction.payment_provider_slug.in_(["mastercard", "amex"]),
            )
            .all()
        )

        for id_tuple in mastercard_and_amex_unmatched_transaction_ids:
            unmatched_transaction_ids.append(id_tuple[0])

        return unmatched_transaction_ids
