import contextlib
import secrets
import inspect

from functools import partial
from unittest import mock

from flask import url_for
import pytest
from sqlalchemy.orm import Session

from app import db
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


@pytest.fixture
def session():
    connection = db.engine.connect()
    session = Session(bind=connection)
    transaction = connection.begin_nested()
    try:
        yield session
    finally:
        transaction.rollback()
        session.close()


def test_validate_key():
    with pytest.raises(ValueError):
        config._validate_key("bad-key")
    assert config._validate_key(f"{config.KEY_PREFIX}-good-key") is None


def test_get(redis, token0, session):
    k = make_key("test-get-0")
    config_item = models.ConfigItem(key=k, value=token0)
    session.add(config_item)

    assert config.get(k, session=session) == token0
    assert redis.get(k) == token0


def test_get_unset(redis, session):
    k = make_key("test-get-unset-0")
    assert config.get(k, session=session) == ""


def test_get_with_default(redis, token0, token1, session):
    k = make_key("test-get-with-default-0")
    config_item = models.ConfigItem(key=k, value=token0)
    session.add(config_item)
    redis.set(k, token0)
    assert config.get(k, default=token1, session=session) == token0


def test_get_unset_with_default(redis, token0, session):
    k = make_key("test-get-unset-with-default-0")
    config_item = models.ConfigItem(key=k, value=token0)
    session.add(config_item)
    assert config.get(k, default=token0, session=session) == token0
    assert config.get(k, session=session) == token0, "The previous get should have created a new pair in redis"


def test_update(redis, token0, token1, session):
    k = make_key("test-update-0")
    config_item = models.ConfigItem(key=k, value=token0)
    session.add(config_item)
    assert config.get(k, session=session) == token0
    config.update(k, token1, session=session)
    assert config.get(k, session=session) == token1


def test_update_unset(redis, token0, session):
    k = make_key("test-update-unset-0")
    with pytest.raises(config.ConfigKeyError):
        config.update(k, token0, session=session)


def test_all_keys(redis, token0):
    gen = config.all_keys()
    assert inspect.isgenerator(gen), "all_keys should return a generator"

    realised = list(gen)
    assert len(realised) == 0, "there should be no config keys stored yet"

    k = make_key("test-all-keys-0")
    redis.set(k, token0)

    realised = list(config.all_keys())
    assert realised == [(k, token0)], "there should be a single config key stored"


def test_config_value(redis, token0, token1, session):
    k = make_key("test-config-value-with-default-0")
    cv = config.ConfigValue(k, default=token0, session=session)
    assert cv.key == k
    assert cv.default == token0
    assert cv.__get__(None, None) == token0, "the cv should return its default"
    assert redis.get(k) == token0, "the previous get should have set the default in redis"

    config.update(k, token1, session=session)
    assert cv.__get__(None, None) == token1, "the cv should return the new value despite its default"


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


def test_update_key_api(redis, token0, token1, api_client, session):
    with mock.patch("app.config.views.session_scope", new=partial(contextlib.nullcontext, enter_result=session)):
        k = make_key("test-update-key-api-0")
        resp = api_client.put(url_for("config_api.update_key", key=k), json={"value": token0})
        assert resp.status_code == 400, resp.json

        config_item = models.ConfigItem(key=k, value=token1)
        session.add(config_item)

        resp = api_client.put(url_for("config_api.update_key", key=k), json={"value": token1})
        assert resp.status_code == 200, resp.json
        assert config.get(k, session=session) == token1

        resp = api_client.put(url_for("config_api.update_key", key=k), json={"bad": True})
        assert resp.status_code == 400, resp.json
