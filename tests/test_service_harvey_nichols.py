import pytest
import requests
import responses

from app.service.harvey_nichols import HarveyNicholsAPI


TEST_HARVEY_NICHOLS_URL = "http://harveynichols.test"


@pytest.fixture
def harvey_nichols() -> HarveyNicholsAPI:
    return HarveyNicholsAPI(TEST_HARVEY_NICHOLS_URL)


@responses.activate
def test_merchant_request(harvey_nichols: HarveyNicholsAPI) -> None:
    url = f"{TEST_HARVEY_NICHOLS_URL}/WebCustomerLoyalty/services/CustomerLoyalty/ClaimTransaction"
    body = {"CustomerClaimTransactionResponse": {"outcome": "Success"}}
    responses.add(responses.POST, url, json=body)

    resp = harvey_nichols.claim_transaction("", "", "")
    expected_resp = {"outcome": "Success"}
    assert resp == expected_resp


@responses.activate
def test_merchant_request_bad_500(harvey_nichols: HarveyNicholsAPI) -> None:
    url = f"{TEST_HARVEY_NICHOLS_URL}/WebCustomerLoyalty/services/CustomerLoyalty/ClaimTransaction"
    body = {"bad_request": {"outcome": "error"}}
    responses.add(responses.POST, url, json=body, status=500)

    with pytest.raises(requests.HTTPError) as ex:
        harvey_nichols.claim_transaction("", "", "")
    assert ex.value.response.status_code == 500


@responses.activate
def test_merchant_request_bad_400(harvey_nichols: HarveyNicholsAPI) -> None:
    url = f"{TEST_HARVEY_NICHOLS_URL}/WebCustomerLoyalty/services/CustomerLoyalty/ClaimTransaction"
    body = {"bad_request": {"outcome": "error"}}
    responses.add(responses.POST, url, json=body, status=400)

    with pytest.raises(requests.HTTPError) as ex:
        harvey_nichols.claim_transaction("", "", "")
    assert ex.value.response.status_code == 400
