from flask import Flask

from app.api import utils


def test_expects_json():
    app = Flask(__name__)

    @app.route('/')
    @utils.expects_json
    def index():
        return 'This should not pass!'

    client = app.test_client()
    resp = client.get('/')
    assert resp.status_code == 400, resp.json
