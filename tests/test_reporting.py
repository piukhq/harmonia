from logging import Logger

import pytest

from app.reporting import get_logger


def test_get_valid_logger():
    l = get_logger('test')
    assert isinstance(l, Logger)


def test_get_logger_with_short_tag():
    with pytest.raises(AssertionError):
        get_logger('te')


def test_get_logger_with_long_tag():
    with pytest.raises(AssertionError):
        get_logger('testtest')
