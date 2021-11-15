import typing as t
from functools import cached_property

import rq
from tenacity import retry, stop_after_attempt, wait_exponential

from app import config, db, models, reporting
from app.core import export_director, identifier, import_director, matching_worker

log = reporting.get_logger("tasks")


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
        result = super().enqueue(f, retry=rq.Retry(max=3, interval=[10, 30, 60]), *args, **kwargs)
        log.debug(f"Task {f.__name__} enqueued on queue {self.name}")
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
export_queue = LoggedQueue(name="export", connection=db.redis_raw)


def import_scheme_transactions(scheme_transactions: t.List[models.SchemeTransaction], *, match_group: str) -> None:
    log.debug(f"Task started: import {len(scheme_transactions)} scheme transactions in group {match_group}.")
    director = import_director.SchemeImportDirector()

    with db.session_scope() as session:
        director.handle_scheme_transactions(scheme_transactions, match_group=match_group, session=session)


def import_auth_payment_transactions(
    payment_transactions: t.List[models.PaymentTransaction], *, match_group: str
) -> None:
    log.debug(f"Task started: import {len(payment_transactions)} auth payment transactions.")
    director = import_director.PaymentImportDirector()

    with db.session_scope() as session:
        # TODO: replace with batch process
        for payment_transaction in payment_transactions:
            director.handle_auth_payment_transaction(payment_transaction, session=session)


def import_settled_payment_transactions(
    payment_transactions: t.List[models.PaymentTransaction], *, match_group: str
) -> None:
    log.debug(f"Task started: import {len(payment_transactions)} settled payment transactions.")
    director = import_director.PaymentImportDirector()

    with db.session_scope() as session:
        # TODO: replace with batch process
        for payment_transaction in payment_transactions:
            director.handle_settled_payment_transaction(payment_transaction, session=session)


def identify_user(settlement_key: int, merchant_identifier_ids: list, token: str) -> None:
    log.debug(f"Task started: identify user #{settlement_key}")
    with db.session_scope() as session:
        identifier.identify_user(settlement_key, merchant_identifier_ids, token,  session=session)


def identify_payment_transaction(payment_transaction_id: int) -> None:
    log.debug(f"Task started: identify payment transaction #{payment_transaction_id}")
    with db.session_scope() as session:
        identifier.identify_payment_transaction(payment_transaction_id, session=session)


def match_payment_transaction(payment_transaction_id: int) -> None:
    log.debug(f"Task started: match payment transaction #{payment_transaction_id}")
    worker = matching_worker.MatchingWorker()

    with db.session_scope() as session:
        worker.handle_payment_transaction(payment_transaction_id, session=session)


def match_scheme_transactions(match_group: str) -> None:
    log.debug(f"Task started: match scheme transactions in group {match_group}")
    worker = matching_worker.MatchingWorker()

    with db.session_scope() as session:
        worker.handle_scheme_transactions(match_group, session=session)


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
