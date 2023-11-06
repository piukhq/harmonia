import datetime
import logging
from unittest import mock

import pendulum
import pytest

from app.feeds import FeedType
from app.imports.agents.stonegate import Stonegate


@pytest.fixture
def stonegate():
    return Stonegate()


MERCHANT_SLUG = "stonegate"

TRANSACTION_DATA = [
    {
        "transaction_id": "QTZENTY0DdGOEJCQkU3",
        "payment_card_type": "VS",
        "payment_card_first_six": "454546",
        "payment_card_last_four": "6309",
        "amount": 23.99,
        "currency_code": "GBP",
        "auth_code": "188328",
        "date": datetime.datetime(2023, 4, 18, 11, 14, 34, tzinfo=pendulum.timezone("Europe/London")),
        "merchant_identifier": "10209723",
        "retailer_location_id": "store_1a",
        "metadata": {
            "AccountID": "value1",
        },
    }
]


def test_stonegate_instance(stonegate) -> None:
    assert stonegate.provider_slug == "stonegate"
    assert stonegate.feed_type == FeedType.MERCHANT


@pytest.mark.parametrize(
    "test_input,expected_bool,expected_value",
    [("", False, None), (" ", False, None), (None, False, None), ("123", False, None), ("412345", True, "visa")],
)
def test_first_six_valid(test_input, expected_bool, expected_value, stonegate) -> None:
    assert stonegate.first_six_valid(test_input) == expected_bool
    assert stonegate.payment_card_type == expected_value


@pytest.mark.parametrize(
    "test_input,expected",
    [("VISACREDIT", "visa"), ("VISACREDIT", "visa")],
)
def test_get_payment_card_from_payment_card_type(test_input, expected, stonegate):
    stonegate.get_payment_card_from_payment_card_type(test_input)
    assert stonegate.payment_card_type == expected


@mock.patch("app.imports.agents.bases.queue_agent.QueueAgent._do_import")
def test_do_import_with_valid_first_six(mock_base_do_import, stonegate) -> None:
    transaction_data = TRANSACTION_DATA[0]
    transaction_data["payment_card_first_six"] = "412345"

    stonegate._do_import(transaction_data)

    mock_base_do_import.assert_called_once()


@pytest.mark.parametrize("test_input", ["", "      ", None])
def test_do_import_with_null_first_six(test_input, stonegate, caplog) -> None:
    transaction_data = TRANSACTION_DATA[0]
    transaction_data["payment_card_first_six"] = test_input

    stonegate.log.propagate = True
    caplog.set_level(logging.DEBUG)
    stonegate._do_import(transaction_data)

    assert (
        caplog.messages[0] == "Discarding transaction QTZENTY0DdGOEJCQkU3 as the payment_card_first_six field is empty"
    )
    assert len(caplog.messages) == 1


def test_do_import_with_empty_string_first_six(stonegate, caplog) -> None:
    transaction_data = TRANSACTION_DATA[0]
    transaction_data["payment_card_first_six"] = "123"

    stonegate.log.propagate = True
    caplog.set_level(logging.DEBUG)
    stonegate._do_import(transaction_data)

    assert (
        caplog.messages[0] == "Discarding transaction QTZENTY0DdGOEJCQkU3 as the payment_card_first_six "
        "field does not contain 6 characters"
    )
    assert len(caplog.messages) == 1


@pytest.mark.parametrize("test_input", ["154546", "lskjdh"])
def test_do_import_with_unrecognised_first_six(test_input: str, stonegate, caplog) -> None:
    transaction_data = TRANSACTION_DATA[0]
    transaction_data["payment_card_first_six"] = test_input

    stonegate.log.propagate = True
    caplog.set_level(logging.DEBUG)
    stonegate._do_import(transaction_data)

    assert (
        caplog.messages[0]
        == "Discarding transaction QTZENTY0DdGOEJCQkU3 as the payment_card_first_six is not recognised"
    )
    assert len(caplog.messages) == 1


@pytest.mark.parametrize(
    "test_input,expected", [("412345", "visa"), ("212345", "mastercard"), ("512345", "mastercard"), ("312345", "amex")]
)
def test_to_transaction_fields(test_input: str, expected: str) -> None:
    transaction_data = TRANSACTION_DATA[0]
    transaction_data["payment_card_first_six"] = test_input

    scheme_transaction_fields = Stonegate().to_transaction_fields(transaction_data)

    assert scheme_transaction_fields._asdict() == {
        "merchant_slug": MERCHANT_SLUG,
        "payment_provider_slug": expected,
        "transaction_date": pendulum.DateTime(2023, 4, 18, 11, 14, 34, tzinfo=pendulum.timezone("Europe/London")),
        "has_time": True,
        "spend_amount": 2399,
        "spend_multiplier": 100,
        "spend_currency": "GBP",
        "first_six": test_input,
        "last_four": "6309",
        "auth_code": "188328",
        "extra_fields": {"account_id": "value1"},
    }
