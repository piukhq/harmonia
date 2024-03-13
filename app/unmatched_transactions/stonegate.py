import pendulum
from sqlalchemy import and_, or_

from app import db, models
from app.config import KEY_PREFIX, Config, ConfigValue
from app.feeds import FeedType
from app.unmatched_transactions.base import BaseAgent

PROVIDER_SLUG = "stonegate"
SCHEDULE_KEY = f"{KEY_PREFIX}agents.unmatched_transactions.{PROVIDER_SLUG}.schedule"


class Stonegate(BaseAgent):
    provider_slug = f"{PROVIDER_SLUG}_unmatched"

    config = Config(
        ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *"),
    )

    def __init__(self):
        super().__init__()

    def find_unmatched_transactions(self, session: db.Session) -> list[int]:
        query = (
            session.query(models.Transaction.id)
            .join(
                models.PaymentTransaction,
                models.Transaction.transaction_id == models.PaymentTransaction.transaction_id,
            )
            .filter(
                models.PaymentTransaction.status == models.TransactionStatus.PENDING.name,
                models.Transaction.merchant_slug == "stonegate",
                or_(
                    and_(
                        models.Transaction.payment_provider_slug == "visa",
                        models.Transaction.feed_type != FeedType.REFUND.name,
                        models.Transaction.transaction_date < pendulum.now().date().subtract(days=2),
                    ),
                    and_(
                        models.Transaction.payment_provider_slug.in_(["mastercard", "amex"]),
                        models.Transaction.feed_type == FeedType.SETTLED.name,
                    ),
                ),
            )
        )
        return [id for (id,) in query]
