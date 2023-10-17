import datetime

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
            "account_id": "value1",
        },
    }
]


def test_stonegate_instance(stonegate) -> None:
    assert stonegate.provider_slug == "stonegate"
    assert stonegate.feed_type == FeedType.MERCHANT


def test_to_transaction_fields() -> None:
    scheme_transaction_fields = Stonegate().to_transaction_fields(TRANSACTION_DATA[0])
    assert scheme_transaction_fields._asdict() == {
        "merchant_slug": MERCHANT_SLUG,
        "payment_provider_slug": "visa",
        "transaction_date": pendulum.DateTime(2023, 4, 18, 11, 14, 34, tzinfo=pendulum.timezone("Europe/London")),
        "has_time": True,
        "spend_amount": 23.99,
        "spend_multiplier": 100,
        "spend_currency": "GBP",
        "first_six": None,
        "last_four": "6309",
        "auth_code": "188328",
        "extra_fields": {"account_id": "value1"},
    }
