from flask import Flask, jsonify, request

from .base import BaseAgent, log


class PassiveAPIAgent(BaseAgent):
    def _create_app(self) -> Flask:
        app = Flask(__name__)

        @app.route('/')
        def index() -> str:
            if request.json is None:
                return jsonify({'ok': False, 'reason': 'A JSON body is expected.'})
            self._import_transactions([request.json])
            return jsonify({'ok': True})

        return app

    def run(self, *, immediate: bool = False, debug: bool = True) -> None:
        app = self._create_app()
        log.warning(
            'This agent should only be run this way for local testing and development. '
            'A production deployment should utilise a server such as uWSGI or Gunicorn.')
        app.run()
