import inspect
import typing as t

from flask import Flask, jsonify, request

from app.imports.agents.bases.base import BaseAgent


class PassiveAPIAgent(BaseAgent):
    def create_app(self, *, debug=False) -> Flask:
        env = "development" if debug else "production"
        app = Flask(__name__)
        app.config["DEBUG"] = debug
        app.config["ENV"] = env

        @app.route("/", methods=["POST"])
        def index() -> str:
            if request.json is None:
                return jsonify({"ok": False, "reason": "A JSON body is expected."})
            transactions_data = self.extract_transactions(request.json)
            transactions_data = self.get_schema().load(transactions_data, many=True)
            self._import_transactions(transactions_data, source="POST /")
            return jsonify({"ok": True})

        return app

    def extract_transactions(
        self, request_json: t.Dict[str, str]
    ) -> t.List[t.Dict[str, str]]:
        return [request_json]

    def run(self, *, once: bool = False) -> None:
        if self.debug is True:
            app = self.create_app(debug=True)
            app.run()
        else:
            self.log.warning(
                "This agent should only be run this way for local testing and development. "
                "A production deployment should utilise a server such as uWSGI or Gunicorn. "
                f"The WSGI callable is `{self.__module__}.app`. "
                "Run with --debug if you actually want to use this CLI."
            )

    def _help(self, module, wsgi_file):
        return inspect.cleandoc(
            f"""
            This is an agent based on the PassiveAPIAgent base class.
            It can be run through the txmatch_import CLI for local testing and development if the --debug flag is given.

            For a production deployment, a WSGI compatible server such as uWSGI or Gunicorn should be used.
            Examples:
            * uWSGI: uwsgi --http 127.0.0.1:8080 --wsgi-file {wsgi_file} --callable app
            * Gunicorn: gunicorn -b 127.0.0.1:8080 {module}:app
            """
        )
