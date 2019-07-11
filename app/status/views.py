from flask import Blueprint, jsonify

from app import db, models
from app.status import status_monitor, schemas
from app.api.utils import ResponseType
import settings

api = Blueprint("status_api", __name__, url_prefix=f"{settings.URL_PREFIX}/status")


@api.route("/")
def get_status():
    """---
    get:
      description: Get status report
      responses:
        200:
          description: The status report.
          schema: StatusReportSchema
    """
    schema = schemas.StatusReportSchema()
    data = schema.dump(status_monitor.report()).data
    errors = schema.validate(data)
    if errors:
        raise ValueError(errors)
    return jsonify(data)


@api.route("/transaction/lookup/<transaction_id>")
def lookup_transaction(transaction_id: str) -> ResponseType:
    import_transaction = db.run_query(
        lambda: db.session.query(models.ImportTransaction)
        .filter(models.ImportTransaction.transaction_id == transaction_id)
        .first()
    )

    if not import_transaction:
        return jsonify({"error": f"Could not find an imported transaction with ID: {transaction_id}"}), 404

    scheme_transaction = db.run_query(
        lambda: db.session.query(models.SchemeTransaction)
        .filter(models.SchemeTransaction.transaction_id == import_transaction.transaction_id)
        .first()
    )
    payment_transaction = None
    if not scheme_transaction:
        payment_transaction = db.run_query(
            lambda: db.session.query(models.PaymentTransaction)
            .filter(models.PaymentTransaction.transaction_id == import_transaction.transaction_id)
            .first()
        )

    def get_matched_transaction():
        q = db.session.query(models.MatchedTransaction)
        if scheme_transaction:
            q = q.filter(models.MatchedTransaction.scheme_transaction_id == scheme_transaction.id)
        if payment_transaction:
            q = q.filter(models.MatchedTransaction.payment_transaction_id == payment_transaction.id)
        return q.first()

    matched_transaction = db.run_query(get_matched_transaction)

    if matched_transaction:
        scheme_transaction = matched_transaction.scheme_transaction
        payment_transaction = matched_transaction.payment_transaction
        export_transaction = db.run_query(
            lambda: db.session.query(models.ExportTransaction)
            .filter(models.ExportTransaction.matched_transaction_id == matched_transaction.id)
            .first()
        )
    else:
        export_transaction = None

    def f(model, *fields):
        return {f: getattr(model, f) for f in fields}

    schema = schemas.TransactionLookupSchema()
    data = schema.dump(
        {
            "import_transaction": import_transaction,
            "scheme_transaction": scheme_transaction,
            "payment_transaction": payment_transaction,
            "matched_transaction": matched_transaction,
            "export_transaction": export_transaction,
        }
    ).data

    return jsonify(data)
