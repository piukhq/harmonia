from unittest import mock

import pytest
import responses

from app.service.bpl import BplAPI

TEST_BPL_URL = "http://bpl.test/mock"

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

response_200 = {"transaction_id": "BPL1234567890", "transaction_status": "Awarded"}

response_400_error = {"display_message": "Malformed request.", "code": "MALFORMED_REQUEST"}

response_500_error = {
    "Type": "ServiceException",
    "Code": "InternalServerError",
    "Description": 'Cannot open database "Synch" requested by the login. '
    "The login failed.\r\nLogin failed for user 'Bpl_Api'.",
}


@pytest.fixture
def bpl() -> BplAPI:
    return BplAPI(TEST_BPL_URL, "bpl-merchant")


@responses.activate
@mock.patch("app.service.bpl.BplAPI.get_security_token")
def test_merchant_request(mock_get_security_token, bpl: BplAPI) -> None:
    mock_get_security_token.return_value = "mocked_token"
    url = f"{TEST_BPL_URL}/bpl-merchant/transaction"
    responses.add(responses.POST, url=url, json=response_200, status=200)

    resp = bpl.post_matched_transaction("bpl-merchant", request_data)

    assert resp.json() == response_200
    assert resp.status_code == 200


@responses.activate
@mock.patch("app.service.bpl.BplAPI.get_security_token")
def test_merchant_request_500(mock_get_security_token, bpl: BplAPI) -> None:
    mock_get_security_token.return_value = "mocked_token"
    url = f"{TEST_BPL_URL}/bpl-merchant/transaction"
    responses.add(responses.POST, url, json=response_500_error, status=500)

    resp = bpl.post_matched_transaction("bpl-merchant", request_data)

    assert resp.json() == response_500_error
    assert resp.status_code == 500


@responses.activate
@mock.patch("app.service.bpl.BplAPI.get_security_token")
def test_merchant_request_bad_400(mock_get_security_token, bpl: BplAPI) -> None:
    mock_get_security_token.return_value = "mocked_token"
    url = f"{TEST_BPL_URL}/bpl-merchant/transaction"
    responses.add(responses.POST, url, json=response_400_error, status=400)

    resp = bpl.post_matched_transaction("bpl-merchant", request_data)

    assert resp.json() == response_400_error
    assert resp.status_code == 400
