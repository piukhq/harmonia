import typing as t

from apispec import APISpec
from apispec_webframeworks.flask import FlaskPlugin
from apispec.ext.marshmallow import MarshmallowPlugin
import flask
import flask_cors

from app.version import __version__
import settings

spec = APISpec(
    title="Transaction Matching API",
    version=__version__,
    openapi_version="2.0",
    plugins=[FlaskPlugin(), MarshmallowPlugin()],
    info={"description": "Management API for the transaction matching system."},
)


def define_schema(schema_class: t.Type) -> t.Type:
    """A decorator to automatically define an apispec schema for a class."""
    spec.components.schema(schema_class.__name__, schema=schema_class)
    return schema_class


def create_app() -> flask.Flask:
    app = flask.Flask(__name__)
    app.config.from_mapping(settings.FLASK)  # type: ignore

    flask_cors.CORS(app)

    from app.api.views import api as core_api
    from app.config.views import api as config_api
    from app.status.views import api as status_api
    from app.mids.views import api as mids_api

    app.register_blueprint(core_api)
    app.register_blueprint(config_api)
    app.register_blueprint(status_api)
    app.register_blueprint(mids_api)

    with app.test_request_context():
        for view_func in app.view_functions.values():
            spec.path(view=view_func)

    return app


app = create_app()
