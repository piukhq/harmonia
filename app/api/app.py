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


def register_import_agent_routes(app: flask.Flask) -> None:
    from app.imports.agents import PassiveAPIAgent
    from app.imports.agents.registry import import_agents

    for slug in import_agents._entries:
        agent = import_agents.instantiate(slug)
        if isinstance(agent, PassiveAPIAgent):
            bp = agent.get_blueprint()
            app.register_blueprint(bp)


def create_app() -> flask.Flask:
    app = flask.Flask(__name__)
    app.config.from_mapping(settings.FLASK)  # type: ignore

    flask_cors.CORS(app)

    from azure_oidc.integrations.flask_decorator import HTTPUnauthorized

    @app.errorhandler(HTTPUnauthorized)
    def handle_unauthorized(error: HTTPUnauthorized):
        return {"title": "401 Unauthorized", "description": error.description}, 401

    from app.api.views import api as core_api
    from app.config.views import api as config_api
    from app.matching.views import api as matching_api
    from app.mids.views import api as mids_api
    from app.status.views import api as status_api

    app.register_blueprint(core_api)
    app.register_blueprint(config_api)
    app.register_blueprint(status_api)
    app.register_blueprint(mids_api)
    app.register_blueprint(matching_api)

    register_import_agent_routes(app)

    with app.test_request_context():
        for view_func in app.view_functions.values():
            spec.path(view=view_func)

    return app


app = create_app()
