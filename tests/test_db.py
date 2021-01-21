from unittest import mock

from sqlalchemy.exc import IntegrityError

from app import db
from app.models import ConfigItem


def test_get_or_create(db_session):
    assert db._get_one_or_none(ConfigItem, key="potato", session=db_session) is None

    ci, created = db.get_or_create(ConfigItem, key="potato", defaults={"value": "mashed"}, session=db_session)
    assert created is True
    assert ci.value == "mashed"

    ci, created = db.get_or_create(ConfigItem, key="potato", defaults={"value": "baked"}, session=db_session)
    assert created is False
    assert ci.value == "mashed"


def test_get_or_create_integrity_error(db_session):
    with mock.patch("app.db.run_query") as mock_run_query:
        mock_run_query.side_effect = [
            None,
            IntegrityError("<...statement...>", params=(), orig=Exception()),
            ConfigItem(key="potato", value="boiled"),
        ]
        ci, created = db.get_or_create(ConfigItem, key="potato", defaults={"value": "chipped"}, session=db_session)
        assert created is False
        assert ci.value == "boiled"
