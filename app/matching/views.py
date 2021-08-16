import marshmallow
from flask import Blueprint, request

import settings
from app import db
from app.api.auth import auth_decorator
from app.core.matching_worker import MatchingWorker
from app.matching import schemas

api = Blueprint("matching_api", __name__, url_prefix=f"{settings.URL_PREFIX}/matching")
requires_auth = auth_decorator()


@api.route("/force_match", methods=["POST"])
@requires_auth(auth_scopes="transactions:write")
def force_match():
    """Manually create a match between two transactions
    ---
    post:
      description: Manually create a match between two transactions
      parameters:
      - in: body
        schema: ForceMatchRequestSchema
      responses:
        204:
          description: Match was created successfully
        400:
          description: Request did not match expected schema
    """
    request_schema = schemas.ForceMatchRequestSchema()

    try:
        data = request_schema.load(request.json)
    except marshmallow.ValidationError as ex:
        return ex.messages, 400

    worker = MatchingWorker()

    try:
        with db.session_scope() as session:
            worker.force_match(
                data["payment_transaction_id"],
                data["scheme_transaction_id"],
                session=session,
            )
    except worker.RedressError as ex:
        return {"error": str(ex)}, 400

    return "", 204
