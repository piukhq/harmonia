import pendulum
import pytest

from app.feeds import FeedType
from app.imports.agents.costa import Costa


@pytest.fixture
def costa():
    return Costa()


MERCHANT_SLUG = "costa"


TRANSACTION_DATA = [
    {
        "transaction_id": "test_transaction_id_1",
        "payment_card_type": "visa",
        "payment_card_first_six": "666666",
        "payment_card_last_four": "4444",
        "amount": 23.99,
        "currency_code": "GBP",
        "auth_code": "188328",
        "date": pendulum.DateTime(2023, 4, 18, 11, 14, 34, tzinfo=pendulum.timezone("Europe/London")),
        "merchant_identifier": "10209723",
        "retailer_location_id": "store_1a",
        "metadata": {"something": "data"},
        "items_ordered": '{"products":[{"id":"2","productUuid":"534084a0-a6a3-11ec-b020-211a45f43f11"}]}',
    }
]


def test_costa_instance(costa):
    assert costa.provider_slug == "costa"
    assert costa.feed_type == FeedType.MERCHANT


def test_to_transaction_fields() -> None:
    scheme_transaction_fields = Costa().to_transaction_fields(TRANSACTION_DATA[0])
    assert scheme_transaction_fields._asdict() == {
        "merchant_slug": MERCHANT_SLUG,
        "payment_provider_slug": "visa",
        "transaction_date": pendulum.DateTime(2023, 4, 18, 11, 14, 34, tzinfo=pendulum.timezone("Europe/London")),
        "has_time": True,
        "spend_amount": 2399,
        "spend_multiplier": 100,
        "spend_currency": "GBP",
        "first_six": "666666",
        "last_four": "4444",
        "auth_code": "188328",
        "extra_fields": {
            "metadata": {"something": "data"},
            "items_ordered": '{"products":[{"id":"2","productUuid":"534084a0-a6a3-11ec-b020-211a45f43f11"}]}',
        },
    }
