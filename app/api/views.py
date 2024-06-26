import flask

import settings
from app.api.app import spec

api = flask.Blueprint("core_api", __name__, url_prefix=settings.URL_PREFIX)


@api.route("/spec.<fmt>")
def get_api_spec(fmt):
    if fmt not in ["json", "yaml"]:
        return {"error": "format must be json or yaml"}, 400
    if fmt == "json":
        return spec.to_dict()
    else:
        return spec.to_yaml()


@api.route("/spec")
def get_api_spec_ui():
    return flask.render_template("redoc.html")
