import flask
import flask_login
import flask_admin

from app.api.app import spec
from app.api import forms, auth

api = flask.Blueprint("core_api", __name__)


@api.route("/spec.<fmt>")
def get_api_spec(fmt):
    if fmt not in ["json", "yaml"]:
        return flask.jsonify({"error": "format must be json or yaml"}), 400
    if fmt == "json":
        return flask.jsonify(spec.to_dict())
    else:
        return spec.to_yaml()


@api.route("/spec")
def get_api_spec_ui():
    return flask.render_template("redoc.html")


class AdminIndexView(flask_admin.AdminIndexView):
    @flask_admin.expose("/")
    def index(self):
        if not flask_login.current_user.is_authenticated:
            return flask.redirect(flask.url_for(".login_view"))
        return super().index()

    @flask_admin.expose("/login", methods=("GET", "POST"))
    def login_view(self):
        form = forms.LoginForm()
        if form.validate_on_submit():
            try:
                user = auth.get_user(form.email_address.data)
            except Exception:
                flask.flash("Login failed.")
                return flask.redirect(flask.url_for(".login_view"))

            if not auth.validate_password(form.password.data, user.instance.password_hash):
                flask.flash("Login failed.")
                return flask.redirect(flask.url_for(".login_view"))

            flask_login.login_user(user)

        if flask_login.current_user.is_authenticated:
            return flask.redirect(flask.url_for(".index"))

        self._template_args["form"] = form
        return super().index()

    @flask_admin.expose("/logout")
    def logout_view(self):
        flask_login.logout_user()
        return flask.redirect(flask.url_for(".index"))
