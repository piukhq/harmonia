from flask import request, Blueprint
import marshmallow

from app.config import config, schemas
from app.api.utils import expects_json, ResponseType
import settings

api = Blueprint("config_api", __name__, url_prefix=f"{settings.URL_PREFIX}/config")


@api.route("/keys")
def list_keys() -> ResponseType:
    """List config keys
    ---
    get:
      description: List config keys
      responses:
        200:
          description: A list of config keys.
          schema: KeyValuePairSchema
    """
    config_values = list({"key": k, "value": v} for k, v in config.all_keys())

    schema = schemas.KeyValuePairSchema()
    data = schema.dump(config_values, many=True)

    return data


@api.route("/keys/<key>", methods=["PUT"])
@expects_json
def update_key(key: str) -> ResponseType:
    """Update a config key
    ---
    put:
      summary: Update config key
      description: Set the value of a given config key.
      parameters:
      - in: body
        schema: UpdateKeyRequestSchema
      responses:
        200:
          description: The updated key and value.
          schema: KeyValuePairSchema
    """
    request_schema = schemas.UpdateKeyRequestSchema()

    try:
        data = request_schema.load(request.json)
    except marshmallow.ValidationError as ex:
        return ex.messages, 400

    try:
        config.update(key, data["value"])
    except KeyError as e:
        return {"error": str(e).strip('"')}, 400

    response_schema = schemas.KeyValuePairSchema()
    return response_schema.dump({"key": key, "value": config.get(key)})
