import typing as t
from functools import wraps
from urllib.parse import urlparse, urljoin

import flask
import flask_wtf
import wtforms


def error_response(message: str) -> t.Tuple[t.Dict, int]:
    """Returns a standard JSON error response for the given error message."""
    return flask.jsonify({"reason": message}), 400


def expects_json(f: t.Callable) -> t.Callable:
    """A flask view decorator to ensure JSON is present on each request."""

    @wraps(f)
    def ensure_json_is_present(*args, **kwargs):
        if flask.request.json is None:
            return error_response("A JSON body is expected but was not provided.")
        return f(*args, **kwargs)

    return ensure_json_is_present


def is_safe_url(target: str) -> bool:
    """
    Based on [flask snippet #63](http://flask.pocoo.org/snippets/63/)
    """
    ref_url = urlparse(flask.request.host_url)
    test_url = urlparse(urljoin(flask.request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


def get_redirect_target() -> t.Optional[str]:
    """
    Based on [flask snippet #63](http://flask.pocoo.org/snippets/63/)
    """
    next_url = flask.request.args.get("next")
    if next_url and is_safe_url(next_url):
        return next_url
    return None


class RedirectForm(flask_wtf.Form):
    next = wtforms.HiddenField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.next.data:
            self.next.data = get_redirect_target() or None

    def redirect(self, endpoint="index", **values):
        target = self.next.data
        if target is not None and is_safe_url(target):
            return flask.redirect(target)
        target = get_redirect_target()
        return flask.redirect(target or flask.url_for(endpoint, **values))
