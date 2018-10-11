import pytest

from requests.exceptions import ConnectionError

from app.core import http


def test_retry_session():
    s = http.requests_retry_session()
    resp = s.get('https://httpbin.org/get')
    assert resp.status_code == 200


def test_retry_delayed():
    s = http.requests_retry_session(retries=0)
    with pytest.raises(ConnectionError):
        s.get('https://httpbin.org/delay/30', timeout=1)
