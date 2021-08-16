from flask import Blueprint

import settings
from app import db, models
from app.api.auth import auth_decorator
from app.api.utils import ResponseType, view_session
from app.status import schemas, status_monitor

api = Blueprint("status_api", __name__, url_prefix=f"{settings.URL_PREFIX}/status")
requires_auth = auth_decorator()


@api.route("/")
@requires_auth(auth_scopes="status:read")
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
    data = schema.dump(status_monitor.report())
    errors = schema.validate(data)
    if errors:
        raise ValueError(errors)
    return data


@api.route("/transaction/lookup/<transaction_id>")
@requires_auth(auth_scopes="transactions:read")
@view_session
def lookup_transaction(transaction_id: str, *, session: db.Session) -> ResponseType:
    import_transaction = db.run_query(
        lambda: session.query(models.ImportTransaction)
        .filter(models.ImportTransaction.transaction_id == transaction_id)
        .first(),
        session=session,
        read_only=True,
        description=f"find import transaction {transaction_id}",
    )

    if not import_transaction:
        return {"error": f"Could not find an imported transaction with ID: {transaction_id}"}, 404

    scheme_transaction = db.run_query(
        lambda: session.query(models.SchemeTransaction)
        .filter(models.SchemeTransaction.transaction_id == import_transaction.transaction_id)
        .first(),
        session=session,
        read_only=True,
        description=f"find scheme transaction {transaction_id}",
    )
    payment_transaction = None
    if not scheme_transaction:
        payment_transaction = db.run_query(
            lambda: session.query(models.PaymentTransaction)
            .filter(models.PaymentTransaction.transaction_id == import_transaction.transaction_id)
            .first(),
            session=session,
            read_only=True,
            description=f"find payment transaction {transaction_id}",
        )

    def get_matched_transaction():
        q = session.query(models.MatchedTransaction)
        if scheme_transaction:
            q = q.filter(models.MatchedTransaction.scheme_transaction_id == scheme_transaction.id)
        if payment_transaction:
            q = q.filter(models.MatchedTransaction.payment_transaction_id == payment_transaction.id)
        return q.first()

    matched_transaction = db.run_query(
        get_matched_transaction, session=session, read_only=True, description="find matched transaction"
    )

    if matched_transaction:
        scheme_transaction = matched_transaction.scheme_transaction
        payment_transaction = matched_transaction.payment_transaction
        export_transaction = db.run_query(
            lambda: session.query(models.ExportTransaction)
            .filter(models.ExportTransaction.matched_transaction_id == matched_transaction.id)
            .first(),
            session=session,
            read_only=True,
            description="find exported transactions",
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
    )

    return data
