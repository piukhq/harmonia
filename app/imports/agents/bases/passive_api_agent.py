import inspect
import typing as t

from flask import Blueprint, request
import marshmallow

from app import utils, db
from app.api import utils as api_utils
from app.imports.agents import BaseAgent
import settings


class PassiveAPIAgent(BaseAgent):
    @property
    def schema(self):
        return utils.missing_property(type(self), "schema")

    def get_blueprint(self) -> Blueprint:
        api = Blueprint(
            f"{self.provider_slug} transaction import API",
            __name__,
            url_prefix=f"{settings.URL_PREFIX}/import/{self.provider_slug}",
        )

        @api.route("/", strict_slashes=False, methods=["POST"])
        @api_utils.expects_json
        def index() -> t.Tuple[dict, int]:
            """
            Import transactions
            ---
            post:
                description: Import {} transactions
                responses:
                    200:
                        description: Imported {} successfully
                    400:
                        description: Import failed
            """

            try:
                data = self.schema.load(request.json)
            except marshmallow.ValidationError as ex:
                return {"ok": False, "errors": ex.messages}, 400
            transactions_data = self.extract_transactions(data)

            with db.session_scope() as session:
                self._import_transactions(transactions_data, session=session, source="POST /")
            return {"ok": True}, 200

        index.__doc__ = index.__doc__.format(self.provider_slug, self.provider_slug)

        return api

    def extract_transactions(self, request_json: t.Dict[str, str]) -> t.List[t.Dict[str, str]]:
        return [request_json]

    def run(self) -> None:
        self.log.warning(
            "This agent cannot be run this way. "
            "For local testing, use the flask development server. "
            "A production deployment should utilise a server such as Gunicorn. "
        )

    def _help(self, module):
        return inspect.cleandoc(
            f"""
            This is an agent based on the PassiveAPIAgent base class.
            It can be run with the flask development server for local testing and development.

            For a production deployment, a WSGI server such as Gunicorn should be used.

            Endpoint: {settings.URL_PREFIX}/{self.provider_slug}/
            """
        )
