from redis import StrictRedis
from rq import Queue

import settings
from app import models
from app.core import import_director, matching_worker, export_director

redis = StrictRedis.from_url(settings.REDIS_DSN)

import_queue = Queue(name="import", connection=redis)
matching_queue = Queue(name="matching", connection=redis)
export_queue = Queue(name="export", connection=redis)


def import_scheme_transaction(scheme_transaction: models.SchemeTransaction) -> None:
    director = import_director.SchemeImportDirector()
    director.handle_scheme_transaction(scheme_transaction)


def import_payment_transaction(payment_transaction: models.PaymentTransaction) -> None:
    director = import_director.PaymentImportDirector()
    director.handle_payment_transaction(payment_transaction)


def match_payment_transaction(payment_transaction_id: int) -> None:
    worker = matching_worker.MatchingWorker()
    worker.handle_payment_transaction(payment_transaction_id)


def match_scheme_transaction(scheme_transaction_id: int) -> None:
    worker = matching_worker.MatchingWorker()
    worker.handle_scheme_transaction(scheme_transaction_id)


def export_matched_transaction(matched_transaction_id: int) -> None:
    director = export_director.ExportDirector()
    director.handle_matched_transaction(matched_transaction_id)


def export_single_transaction(pending_export_id: int) -> None:
    director = export_director.ExportDirector()
    director.handle_pending_export(pending_export_id)
