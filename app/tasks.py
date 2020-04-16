import typing as t

import rq

from app import models, db, reporting, config
from app.core import import_director, matching_worker, export_director, identifier


log = reporting.get_logger("tasks")


class LoggedQueue(rq.Queue):
    class Config:
        queue_limit: t.Optional[str] = ""  # this is replaced in __init__

    def __init__(self, name="default", default_timeout=None, connection=None, is_async=True, job_class=None, **kwargs):
        super().__init__(
            name=name,
            default_timeout=default_timeout,
            connection=connection,
            is_async=is_async,
            job_class=job_class,
            **kwargs,
        )

        self.Config.queue_limit = config.ConfigValue(f"{config.KEY_PREFIX}:queue:{self.name}:limit", default="5000")

    def enqueue(self, f, *args, **kwargs):
        log.debug(f"Task {f.__name__} enqueued on queue {self.name}")
        return super().enqueue(f, *args, **kwargs)

    def has_capacity(self) -> bool:
        if self.Config.queue_limit:  # queue limit is defined as optional above
            limit = int(self.Config.queue_limit)
        else:
            limit = 5000
        return self.count < limit


def run_worker(queue_names: t.List[str], *, burst: bool = False):
    if not queue_names:
        log.warning("No queues were passed to tasks.run_worker, exiting early.")
        return  # no queues, nothing to do
    queues = [LoggedQueue(name, connection=db.redis_raw) for name in queue_names]
    worker = rq.Worker(queues, connection=db.redis_raw)
    worker.work(burst=burst)


import_queue = LoggedQueue(name="import", connection=db.redis_raw)
matching_queue = LoggedQueue(name="matching", connection=db.redis_raw)
export_queue = LoggedQueue(name="export", connection=db.redis_raw)


def import_scheme_transaction(scheme_transaction: models.SchemeTransaction) -> None:
    log.debug(f"Task started: import scheme transaction {scheme_transaction}")
    director = import_director.SchemeImportDirector()
    director.handle_scheme_transaction(scheme_transaction)


def import_auth_payment_transaction(payment_transaction: models.PaymentTransaction) -> None:
    log.debug(f"Task started: import auth payment transaction {payment_transaction}")
    director = import_director.PaymentImportDirector()
    director.handle_auth_payment_transaction(payment_transaction)


def import_settled_payment_transaction(payment_transaction: models.PaymentTransaction) -> None:
    log.debug(f"Task started: import settled payment transaction {payment_transaction}")
    director = import_director.PaymentImportDirector()
    director.handle_settled_payment_transaction(payment_transaction)


def identify_payment_transaction(payment_transaction_id: int) -> None:
    log.debug(f"Task started: identify payment transaction #{payment_transaction_id}")
    tx_identifier = identifier.Identifier()
    tx_identifier.identify_payment_transaction(payment_transaction_id)


def match_payment_transaction(payment_transaction_id: int) -> None:
    log.debug(f"Task started: match payment transaction #{payment_transaction_id}")
    worker = matching_worker.MatchingWorker()
    worker.handle_payment_transaction(payment_transaction_id)


def match_scheme_transaction(scheme_transaction_id: int) -> None:
    log.debug(f"Task started: match scheme transaction #{scheme_transaction_id}")
    worker = matching_worker.MatchingWorker()
    worker.handle_scheme_transaction(scheme_transaction_id)


def export_matched_transaction(matched_transaction_id: int) -> None:
    log.debug(f"Task started: export matched transaction #{matched_transaction_id}")
    director = export_director.ExportDirector()
    director.handle_matched_transaction(matched_transaction_id)


def export_singular_transaction(pending_export_id: int) -> None:
    log.debug(f"Task started: handle pending export #{pending_export_id}")
    director = export_director.ExportDirector()
    director.handle_pending_export(pending_export_id)
