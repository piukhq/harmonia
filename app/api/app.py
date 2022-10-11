import typing as t

import flask
import flask_cors
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin

import settings
from app.version import __version__

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

    from azure_oidc.integrations.flask_decorator import HTTPUnauthorized
    from werkzeug.exceptions import BadRequest

    from app.api.auth import AuthError

    @app.errorhandler(HTTPUnauthorized)
    def handle_unauthorized(error: HTTPUnauthorized):
        """Handle an OIDC authentication error."""
        return {"title": "401 Unauthorized", "description": error.description}, 401

    @app.errorhandler(AuthError)
    def handle_auth_error(error: AuthError) -> tuple[dict, int]:
        """Handle a service authentication error."""
        return {"title": "401 Unauthorized", "description": error.args}, 401

    @app.errorhandler(BadRequest)
    def handle_bad_request(error: BadRequest) -> tuple[dict, int]:
        """Handle a bad request."""
        return {"title": "400 Bad Request", "description": error.args}, 400

    from app.api.views import api as core_api
    from app.config.views import api as config_api
    from app.identifiers.views import api as identifiers_api
    from app.matching.views import api as matching_api

    app.register_blueprint(core_api)
    app.register_blueprint(config_api)
    app.register_blueprint(identifiers_api)
    app.register_blueprint(matching_api)

    with app.test_request_context():
        for view_func in app.view_functions.values():
            spec.path(view=view_func)

    return app


app = create_app()
