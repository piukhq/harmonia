import logging
from copy import copy
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
        "transaction_id": "0d4a7e9c6bc066c7ab77c820f44c4ca7b81ec3c3cb6c41e49c93150361b3cf02",
        "payment_card_type": "MS",
        "payment_card_first_six": None,
        "payment_card_last_four": "6309",
        "amount": 23.99,
        "currency_code": "GBP",
        "auth_code": "188328",
        "date": pendulum.datetime(2023, 4, 18, 11, 14, 34, tz=("Europe/London")).isoformat(),
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
    "first_six,payment_card_type,expected_result",
    [
        ("412345", "Nothing", "visa"),
        ("212345", "Nothing", "mastercard"),
        ("312345", "Nothing", "amex"),
        ("", "VISACREDIT", "visa"),
        ("      ", "EDC/Maestro", "mastercard"),
        (None, "americanexpress", "amex"),
        ("123", "american experience", None),
    ],
)
def test_set_payment_card_type(first_six, payment_card_type, expected_result, stonegate) -> None:
    # stonegate._get_payment_card_type(first_six, payment_card_type)
    assert stonegate._get_payment_card_type(first_six, payment_card_type) == expected_result


@mock.patch("app.imports.agents.bases.queue_agent.QueueAgent._do_import")
def test_do_import_with_valid_first_six(mock_base_do_import, stonegate) -> None:
    transaction_data = copy(TRANSACTION_DATA[0])
    transaction_data["payment_card_first_six"] = "412345"
    transaction_data["payment_card_type"] = "Nothing to see here"

    stonegate._do_import(transaction_data)

    mock_base_do_import.assert_called_once()
    assert mock_base_do_import.call_args[0][0]["payment_card_type"] == "visa"


@mock.patch("app.imports.agents.bases.queue_agent.QueueAgent._do_import")
def test_do_import_with_valid_payment_card_type(mock_base_do_import, stonegate) -> None:
    transaction_data = copy(TRANSACTION_DATA[0])
    transaction_data["payment_card_type"] = "VISADEBIT"

    stonegate._do_import(transaction_data)

    mock_base_do_import.assert_called_once()
    assert mock_base_do_import.call_args[0][0]["payment_card_type"] == "visa"


def test_do_import_with_invalid_first_six_and_payment_card_type(stonegate, caplog) -> None:
    transaction_data = copy(TRANSACTION_DATA[0])
    transaction_data["payment_card_first_six"] = None
    transaction_data["payment_card_type"] = "Nothing to see here"

    stonegate.log.propagate = True
    caplog.set_level(logging.DEBUG)
    stonegate._do_import(transaction_data)

    assert (
        caplog.messages[0]
        == "Discarding transaction 82f046333695832acbf56cd9b283606f7c22b4c63cb8e1963abc6d0f935f6417 - unable to get payment card type from "  # noqa
        "payment_card_first_six or payment_card_type fields"
    )
    assert len(caplog.messages) == 1
