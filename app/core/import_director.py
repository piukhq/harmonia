from app import db, models, tasks
from app.feeds import FeedType
from app.matching.agents.registry import matching_agents
from app.reporting import get_logger
from app.streaming.agents.registry import streaming_agents

MATCHING_FEEDS = [FeedType.AUTH, FeedType.SETTLED, FeedType.MERCHANT]
STREAMING_FEEDS = [FeedType.AUTH, FeedType.SETTLED, FeedType.REFUND, FeedType.MERCHANT]


log = get_logger("import-director")


def wanted_by_matching(merchant_slug: str, feed_type: FeedType) -> bool:
    return merchant_slug in matching_agents and feed_type in MATCHING_FEEDS


def wanted_by_streaming(merchant_slug: str, feed_type: FeedType) -> bool:
    return merchant_slug in streaming_agents and feed_type in STREAMING_FEEDS


def handle_transaction(transaction_id: str, feed_type: FeedType, match_group: str, *, session: db.Session) -> None:
    """
    Directs the given transaction to the matching engine and/or streaming engine.
    The chosen route depends on the merchant and feed type.
    """
    log.info(f"Handling {feed_type.name} transaction #{transaction_id}")
    q = (
        session.query(models.Transaction.merchant_slug)
        .filter(models.Transaction.transaction_id == transaction_id, models.Transaction.feed_type == feed_type)
        .scalar
    )
    merchant_slug = db.run_query(
        q,
        session=session,
        read_only=True,
        description=f"load {feed_type.name} transaction #{transaction_id} for routing.",
    )

    if wanted_by_matching(merchant_slug, feed_type):
        log.info(f"{feed_type.name} transaction #{transaction_id} is wanted by matching; enqueueing match job")
        tasks.matching_queue.enqueue(tasks.match_transaction, transaction_id, feed_type, match_group)

    if wanted_by_streaming(merchant_slug, feed_type):
        log.info(f"{feed_type.name} transaction #{transaction_id} is wanted by streaming; enqueueing stream job")
        tasks.streaming_queue.enqueue(tasks.stream_transaction, transaction_id, feed_type)


def handle_transactions(match_group: str, *, session: db.Session) -> None:
    q = (
        session.query(models.Transaction.merchant_slug, models.Transaction.feed_type)
        .distinct()
        .filter(models.Transaction.match_group == match_group)
        .one
    )
    merchant_slug, feed_type = db.run_query(
        q, session=session, read_only=True, description=f"load merchant slug of group #{match_group} for routing."
    )

    log.debug(f"Group #{match_group} contains {merchant_slug} {feed_type.name} transactions.")

    if wanted_by_matching(merchant_slug, feed_type):
        log.info(f"{feed_type.name} group #{match_group} is wanted by matching; enqueueing match job")
        tasks.matching_queue.enqueue(tasks.match_transactions, match_group)

    if wanted_by_streaming(merchant_slug, feed_type):
        log.info(f"{feed_type.name} group #{match_group} is wanted by streaming; enqueueing stream job")
        tasks.streaming_queue.enqueue(tasks.stream_transactions, match_group)
