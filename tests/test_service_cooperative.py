import pytest
import responses
import requests

from app.service.cooperative import CooperativeAPI


TEST_COOPERATIVE_URL = "http://cooperative.test/mock/any"

valid_response = [
    {"processed": "7deec56b-9ba5-11e9-9b02-3d3e2f734b26-1"},
    {"processed": "7deec56b-9ba5-11e9-9b02-3d3e2f734b26-2"},
]

valid_request = {
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
def cooperative() -> CooperativeAPI:
    return CooperativeAPI(TEST_COOPERATIVE_URL)


@responses.activate
def test_merchant_request(cooperative: CooperativeAPI) -> None:
    url = TEST_COOPERATIVE_URL
    responses.add(responses.POST, url=url, json=valid_response)

    resp = cooperative.export_transactions(valid_request, {})
    assert resp.json() == valid_response


@responses.activate
def test_merchant_request_bad_500(cooperative: CooperativeAPI) -> None:
    url = TEST_COOPERATIVE_URL
    responses.add(responses.POST, url, json=valid_response, status=500)

    with pytest.raises(requests.HTTPError):
        cooperative.export_transactions(valid_request, {})


@responses.activate
def test_merchant_request_bad_400(cooperative: CooperativeAPI) -> None:
    url = TEST_COOPERATIVE_URL
    responses.add(responses.POST, url, json=valid_response, status=400)

    with pytest.raises(requests.HTTPError):
        cooperative.export_transactions(valid_request, {})
