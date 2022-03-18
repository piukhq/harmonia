from app.models import Transaction


class BaseStreamingAgent:

    """
    Override this method in the agent class if there are conditions associated with streaming
    for example, only stream if the transaction is in the stream feed type and is not an Amex Auth
    """

    def should_stream(self, transaction: Transaction) -> bool:
        return True
