import typing as t
from functools import wraps

from flask import jsonify, request


def error_response(message: str) -> t.Tuple[t.Dict, int]:
    """Returns a standard JSON error response for the given error message."""
    return jsonify({"reason": message}), 400


def expects_json(f: t.Callable) -> t.Callable:
    """A flask view decorator to ensure JSON is present on each request."""

    @wraps(f)
    def ensure_json_is_present(*args, **kwargs):
        if request.json is None:
            return error_response("A JSON body is expected but was not provided.")
        return f(*args, **kwargs)

    return ensure_json_is_present
