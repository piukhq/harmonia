from collections.abc import Iterable

import pendulum
from sqlalchemy import and_, any_, or_

from app import db
from app.config import KEY_PREFIX, Config, ConfigValue
from app.feeds import FeedType
from app.models import MerchantIdentifier, PaymentTransaction, Transaction, TransactionStatus, UserIdentity
from app.unmatched_transactions.base import BaseAgent

PROVIDER_SLUG = "stonegate"
SCHEDULE_KEY = f"{KEY_PREFIX}agents.unmatched_transactions.{PROVIDER_SLUG}.schedule"


class Stonegate(BaseAgent):
    provider_slug = f"{PROVIDER_SLUG}-unmatched"

    config = Config(
        ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *"),
    )

    def __init__(self):
        super().__init__()

    def find_unmatched_transactions(
        self, session: db.Session
    ) -> Iterable[tuple[PaymentTransaction, UserIdentity, MerchantIdentifier]]:
        q = (
            session.query(PaymentTransaction, UserIdentity, MerchantIdentifier)
            .join(
                Transaction,
                PaymentTransaction.transaction_id == Transaction.transaction_id,
            )
            .join(
                MerchantIdentifier,
                MerchantIdentifier.id == any_(Transaction.merchant_identifier_ids),
            )
            .join(UserIdentity, UserIdentity.transaction_id == PaymentTransaction.transaction_id)
            .filter(
                PaymentTransaction.status == TransactionStatus.PENDING.name,
                Transaction.merchant_slug == "stonegate",
                Transaction.transaction_date < pendulum.now().date().subtract(days=2),
                or_(
                    and_(
                        Transaction.payment_provider_slug == "visa",
                        Transaction.feed_type != FeedType.REFUND.name,
                    ),
                    and_(
                        Transaction.payment_provider_slug.in_(["mastercard", "amex"]),
                        Transaction.feed_type == FeedType.SETTLED.name,
                    ),
                ),
            )
            .limit(1000)
        )

        yield from db.run_query(
            lambda: q,
            session=session,
            read_only=True,
            description="load streaming data for Stonegate unmatched transactions",
        )
