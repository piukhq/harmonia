import pytest


@pytest.fixture
def client():
    from app.api import app
    return app.test_client()


def test_get_transactions(client):
    resp = client.get('/api/transactions')
    assert resp.status_code == 200
    assert resp.json == {'message': 'listing'}


def test_post_transactions(client):
    resp = client.post('/api/transactions')
    assert resp.status_code == 200
    assert resp.json == {'message': 'creating'}


def test_get_status(client):
    resp = client.get('/api/status')
    assert resp.status_code == 200

    resp_keys = set(r['key'] for r in resp.json['status'])
    assert resp_keys == set(('database', 'stats_database', 'sentry'))
