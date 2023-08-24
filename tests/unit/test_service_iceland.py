import pytest
import responses

from app.service.iceland import IcelandAPI

TEST_ICELAND_URL = "http://iceland.test/mock/any"

json = ""

request_data = {
    "json": {
        "message_uid": "8d187fb8-0248-11ea-92b7-3af9d3be8080",
        "transactions": [
            {
                "record_uid": "qm35vl2e897k46ojv8w1djrgyq0xpzoj",
                "merchant_scheme_id1": "qm35vl2e897k46ojv8w1djrgyq0xpzoj",
                "merchant_scheme_id2": "35573492",
                "transaction_id": "0000943_YF4OTBJP37",
            },
            {
                "record_uid": "0gz91ke80yxp762l7pwqj42ldomvr53x",
                "merchant_scheme_id1": "0gz91ke80yxp762l7pwqj42ldomvr53x",
                "merchant_scheme_id2": "96553073",
                "transaction_id": "0003975_7KB63BB6Y7",
            },
        ],
    },
    "headers": {"Authorization": "Signature my_signature_ok", "X-REQ-TIMESTAMP": "1573232121"},
}

response_200_error = {
    "error_codes": [{"code": "VALIDATION", "description": "Card number must be provided"}],
    "message_uid": "d07fa702-3e5f-11e9-a0ff-f2ddecdc4819",
}

response_500_error = {
    "Type": "ServiceException",
    "Code": "InternalServerError",
    "Description": 'Cannot open database "Synch" requested by the login. '
    "The login failed.\r\nLogin failed for user 'Ice_Api'.",
}


@pytest.fixture
def iceland() -> IcelandAPI:
    return IcelandAPI(TEST_ICELAND_URL)


@responses.activate
def test_merchant_request(iceland: IcelandAPI) -> None:
    url = TEST_ICELAND_URL
    responses.add(responses.POST, url=url, json=json, status=204)

    resp = iceland.merchant_request(request_data)
    expected_resp = json
    assert resp.json() == expected_resp
    assert resp.status_code == 204


@responses.activate
def test_merchant_request_bad_500(iceland: IcelandAPI) -> None:
    url = TEST_ICELAND_URL
    responses.add(responses.POST, url, json=response_500_error, status=500)

    try:
        iceland.merchant_request(request_data)
    except Exception as error:
        error_resp = error
    assert error_resp.response.json() == response_500_error
    assert error_resp.response.status_code == 500


@responses.activate
def test_merchant_request_bad_400(iceland: IcelandAPI) -> None:
    url = TEST_ICELAND_URL
    responses.add(responses.POST, url, json=json, status=400)

    try:
        resp = iceland.merchant_request(request_data)
    except Exception as error:
        resp = error
    assert resp.response.status_code == 400


@responses.activate
def test_merchant_request_bad_200(iceland: IcelandAPI) -> None:
    url = TEST_ICELAND_URL
    responses.add(responses.POST, url, json=response_200_error)

    resp = iceland.merchant_request(request_data)
    assert resp.json() == response_200_error
