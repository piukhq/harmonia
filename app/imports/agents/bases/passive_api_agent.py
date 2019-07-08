import inspect
import typing as t

from flask import Blueprint, jsonify, request

from app import utils
from app.api import utils as api_utils
from app.imports.agents import BaseAgent
import settings


class PassiveAPIAgent(BaseAgent):
    @property
    def schema(self):
        return utils.missing_property(self, "schema")

    def get_blueprint(self) -> Blueprint:
        api = Blueprint(
            f"{self.provider_slug} transaction import API",
            __name__,
            url_prefix=f"{settings.URL_PREFIX}/import/{self.provider_slug}",
        )

        @api.route("/", strict_slashes=False, methods=["POST"])
        @api_utils.expects_json
        def index() -> str:
            _, errors = self.schema.load(request.json)
            if errors:
                return jsonify({"ok": False, "errors": errors})
            transactions_data = self.extract_transactions(request.json)
            self._import_transactions(transactions_data, source="POST /")
            return jsonify({"ok": True})

        return api

    def extract_transactions(self, request_json: t.Dict[str, str]) -> t.List[t.Dict[str, str]]:
        return [request_json]

    def run(self, *, once: bool = False) -> None:
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
