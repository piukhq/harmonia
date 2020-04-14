import secrets
import inspect

from flask import url_for
import pytest

from app.config import config


def make_key(suffix):
    return f"{config.KEY_PREFIX}{suffix}"


@pytest.fixture
def redis():
    from app.db import redis

    yield redis
    redis.flushall()


@pytest.fixture
def token0():
    return secrets.token_urlsafe()


token1 = token0


def test_validate_key():
    with pytest.raises(ValueError):
        config._validate_key("bad-key")
    assert config._validate_key(f"{config.KEY_PREFIX}-good-key") is None


def test_get(redis, token0):
    k = make_key("test-get-0")
    redis.set(k, token0)
    assert config.get(k) == token0


def test_get_with_default(redis, token0, token1):
    k = make_key("test-get-with-default-0")
    redis.set(k, token0)
    assert config.get(k, default=token1) == token0


def test_get_unset(redis):
    k = make_key("test-get-unset-0")
    assert config.get(k) is None


def test_get_unset_with_default(redis, token0):
    k = make_key("test-get-unset-with-default-0")
    assert config.get(k, default=token0) == token0
    assert config.get(k) == token0, "The previous get should have created a new pair in redis"


def test_update(redis, token0, token1):
    k = make_key("test-update-0")
    redis.set(k, token0)
    assert config.get(k) == token0
    config.update(k, token1)
    assert config.get(k) == token1


def test_update_unset(redis, token0):
    k = make_key("test-update-unset-0")
    with pytest.raises(KeyError):
        config.update(k, token0)


def test_all_keys(redis, token0):
    gen = config.all_keys()
    assert inspect.isgenerator(gen), "all_keys should return a generator"

    realised = list(gen)
    assert len(realised) == 0, "there should be no config keys stored yet"

    k = make_key("test-all-keys-0")
    redis.set(k, token0)

    realised = list(config.all_keys())
    assert realised == [(k, token0)], "there should be a single config key stored"


def test_config_value(redis, token0):
    k = make_key("test-config-value-0")
    cv = config.ConfigValue(k)
    assert cv.key == k
    assert cv.default is None
    assert cv.__get__(None, None) is None

    redis.set(k, token0)
    assert cv.__get__(None, None) == token0, "the cv should return the new value"


def test_config_value_with_default(redis, token0, token1):
    k = make_key("test-config-value-with-default-0")
    cv = config.ConfigValue(k, default=token0)
    assert cv.key == k
    assert cv.default == token0
    assert cv.__get__(None, None) == token0, "the cv should return its default"
    assert redis.get(k) == token0, "the previous get should have set the default in redis"

    redis.set(k, token1)
    assert cv.__get__(None, None) == token1, "the cv should return the new value despite its default"


@pytest.fixture
def api_client():
    from app.api.app import create_app

    app = create_app()
    with app.test_request_context():
        yield app.test_client()


def test_list_keys_api(redis, token0, api_client):
    resp = api_client.get(url_for("config_api.list_keys"))
    assert resp.status_code == 200, resp.json
    assert resp.json == {"keys": []}

    k = make_key("test-list-keys-api-0")
    redis.set(k, token0)

    resp = api_client.get(url_for("config_api.list_keys"))
    assert resp.status_code == 200, resp.json
    assert resp.json == {"keys": [{"key": k, "value": token0}]}


def test_update_key_api(redis, token0, token1, api_client):
    k = make_key("test-update-key-api-0")
    resp = api_client.put(url_for("config_api.update_key", key=k), json={"value": token0})
    assert resp.status_code == 400, resp.json

    redis.set(k, token0)
    resp = api_client.put(url_for("config_api.update_key", key=k), json={"value": token1})
    assert resp.status_code == 200, resp.json
    assert redis.get(k) == token1

    resp = api_client.put(url_for("config_api.update_key", key=k), json={"bad": True})
    assert resp.status_code == 400, resp.json
