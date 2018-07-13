from . import config, schemas
from flask import request, jsonify, Blueprint


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
    data, errors = schema.dump(config_values, many=True)

    if errors:
        return jsonify(errors), 500

    return jsonify(data)


@api.route('/keys/<key>', methods=['PUT'])
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

    data, errors = schema.dump({
        'key': key,
        'value': config.get(key),
    })

    if errors:
        return jsonify(errors), 500
    return jsonify(data)
