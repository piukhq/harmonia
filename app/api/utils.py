import typing as t
from functools import wraps

import flask

from app import db

ResponseType = t.Tuple[t.Dict, int]


def error_response(message: str) -> t.Tuple[t.Dict, int]:
    """Returns a standard JSON error response for the given error message."""
    return {"reason": message}, 400


def expects_json(f: t.Callable) -> t.Callable:
    """A flask view decorator to ensure JSON is present on each request."""

    @wraps(f)
    def ensure_json_is_present(*args, **kwargs):
        if flask.request.json is None:
            return error_response("A JSON body is expected but was not provided.")
        return f(*args, **kwargs)

    return ensure_json_is_present


def view_session(f: t.Callable) -> t.Callable:
    """A flask view decorator that creates a database session for use by the wrapped view."""

    @wraps(f)
    def create_view_session(*args, **kwargs):
        with db.session_scope() as session:
            return f(*args, session=session, **kwargs)

    return create_view_session
