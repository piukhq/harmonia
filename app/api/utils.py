from functools import wraps

from flask import request, jsonify


def error_response(message):
    return jsonify({
        'reason': message,
    }), 400


def expects_json(f):
    @wraps(f)
    def ensure_json_is_present(*args, **kwargs):
        if request.json is None:
            return error_response('A JSON body is expected but was not provided.')
        return f(*args, **kwargs)

    return ensure_json_is_present
