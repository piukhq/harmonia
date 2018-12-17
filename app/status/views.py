from flask import Blueprint, jsonify

from app.status import status_monitor, schemas

api = Blueprint("status_api", __name__, url_prefix="/api/status")


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
    data = schema.dump(status_monitor.report())
    errors = schema.validate(data)
    if errors:
        raise ValueError(errors)
    return jsonify(data)
