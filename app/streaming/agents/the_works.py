from app.feeds import FeedType
from app.models import Transaction
from app.streaming.agents.base import BaseStreamingAgent


class TheWorks(BaseStreamingAgent):
    def should_stream(self, transaction: Transaction) -> bool:
        # Refunds for The Works are streamed
        return transaction.feed_type == FeedType.REFUND
