from unittest import mock

import pytest
import responses

from app.service.the_works import TheWorksAPI

TEST_WORKS_URL = "http://givex.test/mock"
TEST_WORKS_FAILOVER_URL = "http://givex.test/mock/failover"

json = ""

request_data = {
    "json": {
        "id": "BPL1234567890",
        "transaction_total": 1750,
        "datetime": 1615890143,
        "MID": "9999988888",
        "loyalty_id": "24eaa5f3-c751-4971-986a-8b925f644f93",
    }
}

response_transaction_history = [
    "123348509238469083",
    "0",
    "0.00",
    "GBP",
    "100",
    [
        [
            "2023-04-06",
            "14:51:11",
            "Increment",
            "100.0",
            "The Works",
            "",
            [],
            "9400499712",
            "32",
            "2023-04-06 14:51:11",
            "2023-04-06 14:51:11",
            "I",
            "0",
            "JJ#540755 - The Works Stores/Bink - The Works Stores Rewards Program - WEB Integration",
            "0",
            "100",
            "0",
            "0",
            "67",
        ]
    ],
    "1",
    "603628-259364940",
    "None",
    "",
]


@pytest.fixture
def the_works() -> TheWorksAPI:
    return TheWorksAPI(TEST_WORKS_URL, TEST_WORKS_FAILOVER_URL)


@responses.activate
@mock.patch("app.service.the_works.TheWorksAPI.get_credentials")
def test_transaction_history_request(mock_get_credentials, the_works: TheWorksAPI) -> None:
    mock_get_credentials.return_value = ("user_id", "password")
    responses.add(responses.POST, url=TEST_WORKS_URL, json=response_transaction_history, status=200)

    _, resp = the_works._history_request(request_data["json"]["loyalty_id"])

    assert resp == response_transaction_history
