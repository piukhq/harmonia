from rq import Queue

from app import models, db, reporting
from app.core import import_director, matching_worker, export_director, identifier


log = reporting.get_logger("tasks")


class LoggedQueue(Queue):
    def __init__(self, name="default", default_timeout=None, connection=None, is_async=True, job_class=None, **kwargs):
        super().__init__(
            name=name,
            default_timeout=default_timeout,
            connection=connection,
            is_async=is_async,
            job_class=job_class,
            **kwargs,
        )

    def enqueue(self, f, *args, **kwargs):
        log.debug(f"Task {f.__name__} enqueued on queue {self.name}")
        return super().enqueue(f, *args, **kwargs)


import_queue = LoggedQueue(name="import", connection=db.redis)
matching_queue = LoggedQueue(name="matching", connection=db.redis)
export_queue = LoggedQueue(name="export", connection=db.redis)


def import_scheme_transaction(scheme_transaction: models.SchemeTransaction) -> None:
    log.debug(f"Task started: import scheme transaction {scheme_transaction}")
    director = import_director.SchemeImportDirector()
    director.handle_scheme_transaction(scheme_transaction)


def import_payment_transaction(payment_transaction: models.PaymentTransaction) -> None:
    log.debug(f"Task started: import payment transaction {payment_transaction}")
    director = import_director.PaymentImportDirector()
    director.handle_payment_transaction(payment_transaction)


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
