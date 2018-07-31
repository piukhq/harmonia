from flask import request, jsonify, Blueprint

from app.config import config, schemas
from app.api.utils import expects_json


api = Blueprint(
    'config_api',
    __name__,
    url_prefix='/api/config')


@api.route('/keys')
def list_keys():
    """List config keys
    ---
    get:
      description: List config keys
      responses:
        200:
          description: A list of config keys.
          schema: KeyValuePairSchema
    """
    config_values = list({
        'key': k,
        'value': v,
    } for k, v in config.all_keys())

    schema = schemas.KeyValuePairSchema()
    data, _ = schema.dump(config_values, many=True)

    return jsonify(data)


@api.route('/keys/<key>', methods=['PUT'])
@expects_json
def update_key(key):
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
    schema = schemas.UpdateKeyRequestSchema()

    data, errors = schema.load(request.json)

    if errors:
        return jsonify(errors), 400

    try:
        config.update(key, data['value'])
    except KeyError as e:
        return jsonify({'error': str(e).strip('"')}), 400

    schema = schemas.KeyValuePairSchema()

    data, _ = schema.dump({
        'key': key,
        'value': config.get(key),
    })

    return jsonify(data)
