from app.feeds import FeedType
from app.models import Transaction
from app.streaming.agents.base import BaseStreamingAgent


class Bpl(BaseStreamingAgent):
    def should_stream(self, transaction: Transaction) -> bool:
        # Refunds for BPL are streamed
        return transaction.feed_type == FeedType.REFUND
