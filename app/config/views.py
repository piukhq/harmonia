from flask import request, Blueprint
import marshmallow

from app.db import session_scope
from app.config import config, schemas, ConfigKeyError
from app.api.utils import expects_json, ResponseType
from app.api.auth import auth_decorator
import settings

api = Blueprint("config_api", __name__, url_prefix=f"{settings.URL_PREFIX}/config")
requires_auth = auth_decorator()


@api.route("/keys")
@requires_auth(auth_scopes="config:read")
def list_keys() -> ResponseType:
    """List config keys
    ---
    get:
      description: List config keys
      responses:
        200:
          description: A list of config keys.
          schema: ConfigKeysListSchema
    """
    config_keys = {"keys": list({"key": k, "value": v} for k, v in config.all_keys())}

    schema = schemas.ConfigKeysListSchema()
    data = schema.dump(config_keys)

    return data


@api.route("/keys/<key>", methods=["PUT"])
@requires_auth(auth_scopes="config:write")
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
        return {"messages": ex.messages}, 400

    with session_scope() as session:
        try:
            config.update(key, data["value"], session=session)
        except ConfigKeyError as e:
            return {"error": str(e).strip('"')}, 400

        else:
            response_schema = schemas.KeyValuePairSchema()
            return response_schema.dump({"key": key, "value": config.get(key, session=session)})
