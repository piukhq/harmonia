import pendulum
import pytest

from app.feeds import FeedType
from app.imports.agents.slim_chickens import SlimChickens


@pytest.fixture
def slim_chickens():
    return SlimChickens()


MERCHANT_SLUG = "slim_chickens"


TRANSACTION_DATA = [
    {
        "transaction_id": "test_transaction_id_1",
        "payment_card_type": "visa",
        "payment_card_first_six": "666666",
        "payment_card_last_four": "4444",
        "amount": 2399,
        "currency_code": "GBP",
        "auth_code": "188328",
        "date": pendulum.DateTime(2023, 4, 18, 11, 14, 34, tzinfo=pendulum.timezone("Europe/London")),
        "merchant_identifier": "10209723",
        "retailer_location_id": "store_1a",
    }
]


def test_slim_chickens_instance(slim_chickens):
    assert slim_chickens.provider_slug == "slim_chickens"
    assert slim_chickens.feed_type == FeedType.MERCHANT


def test_to_transaction_fields() -> None:
    scheme_transaction_fields = SlimChickens().to_transaction_fields(TRANSACTION_DATA[0])
    assert scheme_transaction_fields._asdict() == {
        "merchant_slug": MERCHANT_SLUG,
        "payment_provider_slug": "visa",
        "transaction_date": pendulum.DateTime(2023, 4, 18, 11, 14, 34, tzinfo=pendulum.timezone("Europe/London")),
        "has_time": True,
        "spend_amount": 2399,
        "spend_multiplier": 100,
        "spend_currency": "GBP",
        "first_six": None,
        "last_four": "4444",
        "auth_code": "188328",
        "extra_fields": None,
    }
