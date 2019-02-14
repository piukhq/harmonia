import typing as t

from apispec import APISpec
from apispec_webframeworks.flask import FlaskPlugin
from apispec.ext.marshmallow import MarshmallowPlugin
import flask
import flask_admin
import flask_admin.contrib.sqla
import flask_cors
import flask_login

from app.version import __version__
import settings

spec = APISpec(
    title="Transaction Matching API",
    version=__version__,
    openapi_version="2.0",
    plugins=[FlaskPlugin(), MarshmallowPlugin()],
    info={
        "description": "Management API for the transaction matching system."
    },
)


def define_schema(schema_class: t.Type) -> t.Type:
    """A decorator to automatically define an apispec schema for a class."""
    spec.components.schema(schema_class.__name__, schema=schema_class)
    return schema_class


def add_admin_views(admin):
    from app import models, db

    class ModelView(flask_admin.contrib.sqla.ModelView):
        def is_accessible(self):
            return flask_login.current_user.is_authenticated

        def inaccessible_callback(self, name, **kwargs):
            return flask.redirect(
                flask.url_for("login", next=flask.request.url)
            )

    model_classes = [
        models.Administrator,
        models.ExportTransaction,
        models.ImportTransaction,
        models.LoyaltyScheme,
        models.MatchedTransaction,
        models.MerchantIdentifier,
        models.PaymentProvider,
        models.PaymentTransaction,
        models.PendingExport,
        models.SchemeTransaction,
        models.UserIdentity,
    ]

    for model_class in model_classes:
        admin.add_view(ModelView(model_class, db.session))


def init_login_manager(app: flask.Flask) -> None:
    from app import models, db
    from app.api import auth

    login_manager = flask_login.LoginManager(app)

    @login_manager.user_loader
    def load_user(uid: str) -> auth.User:
        try:
            administrator = (
                db.session.query(models.Administrator)
                .filter(models.Administrator.uid == uid)
                .one()
            )
        except db.NoResultFound:
            return None
        return auth.User(administrator)


def init_admin(app: flask.Flask) -> None:
    from app.api import views

    app.config["FLASK_ADMIN_SWATCH"] = "flatly"
    admin = flask_admin.Admin(
        app,
        name="Transaction Matching",
        template_mode="bootstrap3",
        index_view=views.AdminIndexView(),
        base_template="admin_master.html"
    )
    add_admin_views(admin)


def create_app() -> flask.Flask:
    app = flask.Flask(__name__)
    app.config.from_mapping(settings.FLASK)  # type: ignore

    flask_cors.CORS(app)

    init_login_manager(app)
    init_admin(app)

    from app.api.views import api as core_api
    from app.config.views import api as config_api
    from app.status.views import api as status_api

    app.register_blueprint(core_api)
    app.register_blueprint(config_api)
    app.register_blueprint(status_api)

    with app.test_request_context():
        for view_func in app.view_functions.values():
            spec.path(view=view_func)

    return app


app = create_app()
