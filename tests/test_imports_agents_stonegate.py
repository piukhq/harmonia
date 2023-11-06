import datetime
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
        "transaction_id": "QTZENTY0DdGOEJCQkU3",
        "payment_card_type": "MS",
        "payment_card_first_six": None,
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
    "first_six,payment_card_type,expected_result",
    [
        ("412345", "Nothing", "visa"),
        ("212345", "Nothing", "mastercard"),
        ("312345", "Nothing", "amex"),
        ("", "VISACREDIT", "visa"),
        ("      ", "EDC/Maestro", "mastercard"),
        (None, "americanexpress", "amex"),
        ("123", "american experience", ""),
    ],
)
def test_set_payment_card_type(first_six, payment_card_type, expected_result, stonegate) -> None:
    stonegate._set_payment_card_type(first_six, payment_card_type)
    assert stonegate.payment_card_type == expected_result


@mock.patch("app.imports.agents.bases.queue_agent.QueueAgent._do_import")
def test_do_import_with_valid_first_six(mock_base_do_import, stonegate) -> None:
    transaction_data = copy(TRANSACTION_DATA[0])
    transaction_data["payment_card_first_six"] = "412345"
    transaction_data["payment_card_type"] = "Nothing to see here"

    stonegate._do_import(transaction_data)

    assert stonegate.payment_card_type == "visa"
    mock_base_do_import.assert_called_once()


@mock.patch("app.imports.agents.bases.queue_agent.QueueAgent._do_import")
def test_do_import_with_valid_payment_card_type(mock_base_do_import, stonegate) -> None:
    transaction_data = copy(TRANSACTION_DATA[0])
    transaction_data["payment_card_type"] = "VISADEBIT"

    stonegate._do_import(transaction_data)

    assert stonegate.payment_card_type == "visa"
    mock_base_do_import.assert_called_once()


def test_do_import_with_invalid_first_six_and_payment_card_type(stonegate, caplog) -> None:
    transaction_data = copy(TRANSACTION_DATA[0])
    transaction_data["payment_card_first_six"] = None
    transaction_data["payment_card_type"] = "Nothing to see here"

    stonegate.log.propagate = True
    caplog.set_level(logging.DEBUG)
    stonegate._do_import(transaction_data)

    assert (
        caplog.messages[0] == "Discarding transaction QTZENTY0DdGOEJCQkU3 - unable to get payment card type from "
        "payment_card_first_six or payment_card_type fields"
    )
    assert len(caplog.messages) == 1


@mock.patch("app.imports.agents.bases.queue_agent.QueueAgent._do_import")
def test_to_transaction_fields_from_valid_first_six(mock_base_do_import, stonegate) -> None:
    transaction_data = copy(TRANSACTION_DATA[0])
    transaction_data["payment_card_first_six"] = "432154"
    transaction_data["payment_card_type"] = "Nothing to see here"

    stonegate._do_import(transaction_data)
    scheme_transaction_fields = stonegate.to_transaction_fields(transaction_data)

    assert scheme_transaction_fields._asdict() == {
        "merchant_slug": MERCHANT_SLUG,
        "payment_provider_slug": "visa",
        "transaction_date": pendulum.DateTime(2023, 4, 18, 11, 14, 34, tzinfo=pendulum.timezone("Europe/London")),
        "has_time": True,
        "spend_amount": 2399,
        "spend_multiplier": 100,
        "spend_currency": "GBP",
        "first_six": "432154",
        "last_four": "6309",
        "auth_code": "188328",
        "extra_fields": {"account_id": "value1"},
    }


@mock.patch("app.imports.agents.bases.queue_agent.QueueAgent._do_import")
def test_to_transaction_fields_from_valid_payment_card_type(mock_base_do_import, stonegate) -> None:
    transaction_data = copy(TRANSACTION_DATA[0])
    transaction_data["payment_card_type"] = "VISADEBIT"

    stonegate._do_import(transaction_data)
    scheme_transaction_fields = stonegate.to_transaction_fields(transaction_data)

    assert scheme_transaction_fields._asdict() == {
        "merchant_slug": MERCHANT_SLUG,
        "payment_provider_slug": "visa",
        "transaction_date": pendulum.DateTime(2023, 4, 18, 11, 14, 34, tzinfo=pendulum.timezone("Europe/London")),
        "has_time": True,
        "spend_amount": 2399,
        "spend_multiplier": 100,
        "spend_currency": "GBP",
        "first_six": None,
        "last_four": "6309",
        "auth_code": "188328",
        "extra_fields": {"account_id": "value1"},
    }
