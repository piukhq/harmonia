import hashlib

import pytest
import responses

from app.service.acteol import ActeolAPI

TEST_ACTEOL_URL = "http://acteol.test/"


@pytest.fixture
def acteol() -> ActeolAPI:
    return ActeolAPI(TEST_ACTEOL_URL)


@responses.activate
def test_post_matched_transaction_origin_id_not_found(acteol: ActeolAPI) -> None:
    response = {"Message": "Origin ID not found", "Error": "Internal Error"}
    responses.add(responses.POST, url=f"{TEST_ACTEOL_URL}/PostMatchedTransaction", json=response)

    resp = acteol.post_matched_transaction(
        {"origin_id": hashlib.sha1("test@bink.com".encode()).hexdigest(), "ReceiptNo": "123456789"}, endpoint="/PostMatchedTransaction"
    )
    assert resp.json() == response
