from app.feeds import FeedType
from app.models import Transaction
from app.streaming.agents.base import BaseStreamingAgent


class Asos(BaseStreamingAgent):
    def should_stream(self, transaction: Transaction):
        # Checking to see if the transaction for this agent is a refund
        return True if transaction.feed_type == FeedType.REFUND else False
