from rq import Queue

from app import models, db
from app.core import import_director, matching_worker, export_director, identifier

import_queue = Queue(name="import", connection=db.redis)
matching_queue = Queue(name="matching", connection=db.redis)
export_queue = Queue(name="export", connection=db.redis)


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


def identify_matched_transaction(matched_transaction_id: int) -> None:
    tx_identifier = identifier.Identifier()
    tx_identifier.identify_matched_transaction(matched_transaction_id)


def export_matched_transaction(matched_transaction_id: int) -> None:
    director = export_director.ExportDirector()
    director.handle_matched_transaction(matched_transaction_id)


def export_single_transaction(pending_export_id: int) -> None:
    director = export_director.ExportDirector()
    director.handle_pending_export(pending_export_id)
