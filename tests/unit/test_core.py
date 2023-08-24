import pytest
from requests.exceptions import ConnectionError

from app.core.requests_retry import requests_retry_session


def test_retry_session():
    s = requests_retry_session()
    resp = s.get("https://httpbin.org/get")
    assert resp.status_code == 200


def test_retry_delayed():
    s = requests_retry_session(retries=0)
    with pytest.raises(ConnectionError):
        s.get("https://httpbin.org/delay/30", timeout=1)
