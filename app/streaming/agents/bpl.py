from app.feeds import FeedType
from app.models import Transaction
from app.streaming.agents.base import BaseStreamingAgent


class Bpl(BaseStreamingAgent):
    def should_stream(self, transaction: Transaction) -> bool:
        # Checking to see if the transaction for this agent is a refund
        return True if transaction.feed_type == FeedType.REFUND else False
