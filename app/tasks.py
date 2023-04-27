import typing as t
from functools import cached_property

import redis
import rq
import sentry_sdk
from tenacity import retry, stop_after_attempt, wait_exponential

from app import config, db, models, reporting
from app.core import export_director, identifier, import_director, matching_director, matching_worker, streaming_worker
from app.feeds import FeedType

log = reporting.get_logger("tasks")


class TasksRedisException(Exception):
    """Exception for any redis error bubbling back through rq"""

    pass


class LoggedQueue(rq.Queue):
    def __init__(self, name="default", default_timeout=None, connection=None, is_async=True, job_class=None, **kwargs):
        super().__init__(
            name=name,
            default_timeout=default_timeout,
            connection=connection,
            is_async=is_async,
            job_class=job_class,
            **kwargs,
        )

        self.config = config.Config(
            config.ConfigValue("queue_limit", key=f"{config.KEY_PREFIX}:queue:{self.name}:limit", default="5000")
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=5, min=5),
        reraise=True,
    )
    def enqueue(self, f, *args, **kwargs):
        try:
            result = super().enqueue(f, retry=rq.Retry(max=3, interval=[10, 30, 60]), *args, **kwargs)
            log.debug(f"Task {f.__name__} enqueued on queue {self.name}")
        except redis.RedisError:
            raise TasksRedisException

        return result

    @cached_property
    def queue_limit(self) -> int:
        with db.session_scope() as session:
            ql = self.config.get("queue_limit", session=session)
        return int(ql)

    def has_capacity(self) -> bool:
        return self.count < self.queue_limit


def run_worker(queue_names: t.List[str], *, burst: bool = False, workerclass: t.Type[rq.Worker] = rq.Worker):
    if not queue_names:
        log.warning("No queues were passed to tasks.run_worker, exiting early.")
        return  # no queues, nothing to do
    queues = [LoggedQueue(name, connection=db.redis_raw) for name in queue_names]
    worker = workerclass(queues, connection=db.redis_raw, log_job_description=False)
    worker.work(burst=burst, with_scheduler=True)


import_queue = LoggedQueue(name="import", connection=db.redis_raw)
identify_user_queue = LoggedQueue(name="identify", connection=db.redis_raw)
matching_queue = LoggedQueue(name="matching", connection=db.redis_raw)
matching_slow_queue = LoggedQueue(name="matching_slow", connection=db.redis_raw)
streaming_queue = LoggedQueue(name="streaming", connection=db.redis_raw)
export_queue = LoggedQueue(name="export", connection=db.redis_raw)


def identify_user(
    *, transaction_id: str, feed_type: FeedType, merchant_identifier_ids: list, card_token: str, match_group: str
) -> None:
    log.debug(f"Task started: identify user #{transaction_id}")

    with db.session_scope() as session:
        try:
            identifier.identify_user(transaction_id, merchant_identifier_ids, card_token, session=session)
        except identifier.RetryableLookupFailure:
            event_id = sentry_sdk.capture_exception()
            log.debug(f"Failed to get user info from Hermes. Task will be requeued. Sentry event ID: {event_id}")
            identify_user_queue.enqueue(
                identify_user,
                transaction_id=transaction_id,
                feed_type=feed_type,
                merchant_identifier_ids=merchant_identifier_ids,
                card_token=card_token,
            )
            return
        except Exception as ex:
            log.debug(f"User identification task failed: {repr(ex)}. Failed Hermes requests will be retried.")
            return

    import_queue.enqueue(import_transaction, transaction_id, feed_type, match_group)


def import_transaction(transaction_id: str, feed_type: FeedType, match_group: str) -> None:
    log.debug(f"Task started: import {feed_type.name} transaction #{transaction_id}")

    with db.session_scope() as session:
        import_director.handle_transaction(transaction_id, feed_type, match_group, session=session)


def import_transactions(match_group: str) -> None:
    log.debug(f"Task started: import transactions in group #{match_group}")

    with db.session_scope() as session:
        import_director.handle_transactions(match_group, session=session)


def match_transaction(transaction_id: str, feed_type: FeedType, match_group: str) -> None:
    log.debug(f"Task started: match {feed_type.name} transaction #{transaction_id}")
    director = matching_director.MatchingDirector()

    with db.session_scope() as session:
        director.handle_transaction(transaction_id, feed_type, match_group, session=session)


def match_transactions(match_group: str) -> None:
    log.debug(f"Task started: match transactions in group #{match_group}")
    director = matching_director.MatchingDirector()

    with db.session_scope() as session:
        director.handle_transactions(match_group, session=session)


def persist_scheme_transactions(scheme_transactions: t.List[models.SchemeTransaction], *, match_group: str) -> None:
    log.debug(f"Task started: persist {len(scheme_transactions)} scheme transactions in group {match_group}.")
    director = matching_director.SchemeMatchingDirector()

    with db.session_scope() as session:
        director.handle_scheme_transactions(scheme_transactions, match_group=match_group, session=session)


def persist_auth_payment_transactions(
    payment_transactions: t.List[models.PaymentTransaction], *, match_group: str
) -> None:
    log.debug(f"Task started: persist {len(payment_transactions)} auth payment transactions.")
    director = matching_director.PaymentMatchingDirector()

    with db.session_scope() as session:
        # TODO: replace with batch process
        for payment_transaction in payment_transactions:
            director.handle_auth_payment_transaction(payment_transaction, session=session)


def persist_settled_payment_transactions(
    payment_transactions: t.List[models.PaymentTransaction], *, match_group: str
) -> None:
    log.debug(f"Task started: import {len(payment_transactions)} settled payment transactions.")
    director = matching_director.PaymentMatchingDirector()

    with db.session_scope() as session:
        # TODO: replace with batch process
        for payment_transaction in payment_transactions:
            director.handle_settled_payment_transaction(payment_transaction, session=session)


def match_payment_transaction(settlement_key: str) -> None:
    log.debug(f"Task started: match payment transaction #{settlement_key}")
    worker = matching_worker.MatchingWorker()

    with db.session_scope() as session:
        worker.handle_payment_transaction(settlement_key, session=session)


def match_scheme_transactions(match_group: str) -> None:
    log.debug(f"Task started: match scheme transactions in group {match_group}")
    worker = matching_worker.MatchingWorker()

    with db.session_scope() as session:
        worker.handle_scheme_transactions(match_group, session=session)


def stream_transaction(transaction_id: str, feed_type: FeedType) -> None:
    log.debug(f"Task started: stream transaction #{transaction_id}")
    worker = streaming_worker.StreamingWorker()

    with db.session_scope() as session:
        worker.handle_transaction(transaction_id, feed_type, session=session)


def stream_transactions(match_group: str) -> None:
    log.debug(f"Task started: stream transactions in group #{match_group}")
    worker = streaming_worker.StreamingWorker()

    with db.session_scope() as session:
        worker.handle_transactions(match_group, session=session)


def export_transaction(transaction_id: int) -> None:
    log.debug(f"Task started: export transaction #{transaction_id}")
    director = export_director.ExportDirector()

    with db.session_scope() as session:
        director.handle_export_transaction(transaction_id, session=session)


def export_singular_transaction(pending_export_id: int) -> None:
    log.debug(f"Task started: handle pending export #{pending_export_id}")
    director = export_director.ExportDirector()

    with db.session_scope() as session:
        director.handle_pending_export(pending_export_id, session=session)
