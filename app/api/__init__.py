import typing as t

from apispec import APISpec
from apispec_webframeworks.flask import FlaskPlugin
from apispec.ext.marshmallow import MarshmallowPlugin
from flask import Flask, jsonify, render_template
from flask_cors import CORS

from app.version import __version__

spec = APISpec(
    title='Transaction Matching API',
    version=__version__,
    openapi_version='2.0',
    plugins=[
        FlaskPlugin(),
        MarshmallowPlugin(),
    ],
    info={
        'description': 'Management API for the transaction matching system.',
    },
)


def define_schema(schema_class: t.Type) -> t.Type:
    """A decorator to automatically define an apispec schema for a class."""
    spec.components.schema(schema_class.__name__, schema=schema_class)
    return schema_class


def create_app() -> Flask:
    app = Flask(__name__)

    CORS(app)

    from app.config.views import api as config_api
    from app.status.views import api as status_api
    app.register_blueprint(config_api)
    app.register_blueprint(status_api)

    @app.route('/spec.<fmt>')
    def get_api_spec(fmt):
        if fmt not in ['json', 'yaml']:
            return jsonify({'error': 'format must be json or yaml'}), 400
        if fmt == 'json':
            return jsonify(spec.to_dict())
        else:
            return spec.to_yaml()

    @app.route('/spec')
    def get_api_spec_ui():
        return render_template('redoc.html')

    with app.test_request_context():
        for view_func in app.view_functions.values():
            spec.path(view=view_func)

    return app


app = create_app()
