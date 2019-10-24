import pytest
import responses

from app.service.cooperative import Cooperative


TEST_COOPERATIVE_URL = "http://cooperative.test/mock/any"

json = [
    {"processed": "7deec56b-9ba5-11e9-9b02-3d3e2f734b26-1"},
    {"processed": "7deec56b-9ba5-11e9-9b02-3d3e2f734b26-2"},
]
request_data = {
    "json": {
        "message_uid": "fed057de-f582-11e9-9173-3af9d3be8080",
        "transactions": [
            {
                "record_uid": "fed02a52-f582-11e9-9173-3af9d3be8080",
                "member_id": 8,
                "card_number": "37f140b3-8b5b-4686-b339-9be35ba71fbe",
                "transaction_id": "7deec56b-9ba5-11e9-9b02-3d3e2f734b26-1",
            },
            {
                "record_uid": "fed0569e-f582-11e9-9173-3af9d3be8080",
                "member_id": 7,
                "card_number": "10d58d42-ff8d-41b4-9c02-29f87193f6bc",
                "transaction_id": "7deec56b-9ba5-11e9-9b02-3d3e2f734b26-2",
            },
        ],
    },
    "headers": {"Authorization": "my_mock_prefix my_signature_ok", "X-API-KEY": "my_mock_api_key"},
}


@pytest.fixture
def cooperative() -> Cooperative:
    return Cooperative(TEST_COOPERATIVE_URL)


@responses.activate
def test_merchant_request(cooperative: Cooperative) -> None:
    url = TEST_COOPERATIVE_URL
    responses.add(responses.POST, url=url, json=json)

    resp = cooperative.merchant_request(request_data)
    expected_resp = json
    assert resp.json() == expected_resp


@responses.activate
def test_merchant_request_bad_500(cooperative: Cooperative) -> None:
    url = TEST_COOPERATIVE_URL
    responses.add(responses.POST, url, json=json, status=500)

    try:
        cooperative.merchant_request(request_data)
    except Exception as error:
        error_resp = error
    assert error_resp.response.status_code == 500


@responses.activate
def test_merchant_request_bad_400(cooperative: Cooperative) -> None:
    url = TEST_COOPERATIVE_URL
    responses.add(responses.POST, url, json=json, status=400)

    try:
        resp = cooperative.merchant_request(request_data)
    except Exception as error:
        resp = error
    assert resp.response.status_code == 400
