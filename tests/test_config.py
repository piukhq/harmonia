import contextlib
import secrets
import inspect

from functools import partial
from unittest import mock

from flask import url_for
import pytest

from app.config import config, models


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


def test_get(redis, token0, db_session):
    k = make_key("test-get-0")
    config_item = models.ConfigItem(key=k, value=token0)
    db_session.add(config_item)

    assert redis.get(k) is None
    assert config.get(k, session=db_session) == token0
    assert redis.get(k) == token0


def test_get_unset(redis, db_session):
    k = make_key("test-get-unset-0")
    assert redis.get(k) is None
    assert config.get(k, session=db_session) == ""
    assert redis.get(k) == "", "The previous get should have set this key to empty string"


def test_get_with_default(redis, token0, token1, db_session):
    k = make_key("test-get-with-default-0")
    redis.set(k, token0)
    assert config.get(k, default=token1, session=db_session) == token0
    assert config.get(k, session=db_session) == token0


def test_get_unset_with_default(redis, token0, token1, db_session):
    k = make_key("test-get-unset-with-default-0")
    assert config.get(k, default=token0, session=db_session) == token0
    assert db_session.query(models.ConfigItem).filter_by(key=k).one_or_none().value == token0
    assert redis.get(k) == token0
    assert config.get(k, session=db_session) == token0, "The previous get should have created a new pair in redis"


def test_update(redis, token0, token1, db_session):
    k = make_key("test-update-0")
    config_item = models.ConfigItem(key=k, value=token0)
    db_session.add(config_item)
    assert config.get(k, session=db_session) == redis.get(k) == token0
    config.update(k, token1, session=db_session)
    assert config.get(k, session=db_session) == redis.get(k) == token1


def test_update_unset(redis, token0, db_session):
    k = make_key("test-update-unset-0")
    with pytest.raises(config.ConfigKeyError):
        config.update(k, token0, session=db_session)


def test_all_keys(redis, token0):
    gen = config.all_keys()
    assert inspect.isgenerator(gen), "all_keys should return a generator"

    realised = list(gen)
    assert len(realised) == 0, "there should be no config keys stored yet"

    k = make_key("test-all-keys-0")
    redis.set(k, token0)

    realised = list(config.all_keys())
    assert realised == [(k, token0)], "there should be a single config key stored"


def test_config(redis, token0, token1, db_session):
    k = make_key("test-config-value-with-default-0")
    cv = config.ConfigValue("cv-name", key=k, default=token0)
    assert cv.key == k
    assert cv.default == token0

    config_obj = config.Config(cv)
    assert config_obj.get("cv-name", session=db_session) == token0
    assert redis.get(k) == token0, "the previous get should have set the default in redis"

    config.update(k, token1, session=db_session)
    assert config_obj.get("cv-name", session=db_session) == token1, "the config should return the new value"

    with pytest.raises(config.ConfigError):
        config_obj.get("unknown", session=db_session)


@pytest.fixture
def api_client():
    from app.api import auth

    # replace the requires_auth decorator with a no-op
    auth.auth_decorator = lambda: lambda *args, **kwargs: lambda fn: fn

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


def test_update_key_api(redis, token0, token1, api_client, db_session):
    with mock.patch("app.config.views.session_scope", new=partial(contextlib.nullcontext, enter_result=db_session)):
        k = make_key("test-update-key-api-0")
        resp = api_client.put(url_for("config_api.update_key", key=k), json={"value": token0})
        assert resp.status_code == 400, resp.json

        config_item = models.ConfigItem(key=k, value=token1)
        db_session.add(config_item)

        resp = api_client.put(url_for("config_api.update_key", key=k), json={"value": token1})
        assert resp.status_code == 200, resp.json
        assert config.get(k, session=db_session) == token1

        resp = api_client.put(url_for("config_api.update_key", key=k), json={"bad": True})
        assert resp.status_code == 400, resp.json
