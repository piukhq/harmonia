import pytest
import responses

import settings
from app.service.hermes import Hermes

TEST_HERMES_URL = "http://hermes.test"


@pytest.fixture
def hermes() -> Hermes:
    return Hermes(TEST_HERMES_URL)


@responses.activate
def test_payment_card_user_info(hermes: Hermes) -> None:
    url = f"{TEST_HERMES_URL}/payment_cards/accounts/payment_card_user_info/test-slug"
    json = {"token123": "1234567890"}
    responses.add(responses.POST, url, json=json)

    resp = hermes.payment_card_user_info("test-slug", "token123")
    assert resp == json


@responses.activate
def test_create_join_scheme_account(hermes: Hermes) -> None:
    url = f"{TEST_HERMES_URL}/accounts/join/test-slug/1"
    json = {"created": True}
    responses.add(responses.POST, url, json=json)

    resp = hermes.create_join_scheme_account("test-slug", 1)
    assert resp == json


def test__slug_format(hermes: Hermes):
    settings.HERMES_SLUGS_TO_FORMAT = ["test-slug1", "test-slug2"]
    settings.HERMES_SLUG_FORMAT_STRING = "{}-mock"
    assert hermes._format_slug("test-slug1") == "test-slug1-mock"
    assert hermes._format_slug("test-slug3") == "test-slug3"

    settings.HERMES_SLUG_FORMAT_STRING = None
    assert hermes._format_slug("test-slug1") == "test-slug1"
