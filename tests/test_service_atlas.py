import pytest

import responses
import requests
import pendulum

from app.service.atlas import Atlas


TEST_ATLAS_URL = "http://atlas.test"


class UserIdentity:
    user_id = 10


class MockTransaction:
    id = 1
    transaction_id = 125
    user_identity = UserIdentity()
    spend_amount = 1500
    transaction_date = pendulum.now()


BINK_ASSIGNED = Atlas.Status.BINK_ASSIGNED


@pytest.fixture
def atlas() -> Atlas:
    return Atlas(TEST_ATLAS_URL)


@responses.activate
def test_save_transaction(atlas: Atlas) -> None:
    url = f"{TEST_ATLAS_URL}/transaction/save"
    body = {
        "TransactionSaved": {
            "id": 176,
            "created_date": "2019-08-08T13:25:03.246697Z",
            "scheme_provider": "test-slug",
            "response": "{'outcome': 'Success'}",
            "transaction_id": "000111441144114411441144",
            "status": "BINK-ASSIGNED",
            "transaction_date": "2019-08-08T14:24:10Z",
            "user_id": "1",
            "amount": 8700,
        }
    }
    responses.add(responses.POST, url, json=body)

    resp = atlas.save_transaction("test-slug", {"outcome": "Success"}, MockTransaction(), BINK_ASSIGNED)
    assert resp == body


@responses.activate
def test_save_transaction_bad_500(atlas: Atlas) -> None:
    url = f"{TEST_ATLAS_URL}/transaction/save"
    body = {"bad_request": {"outcome": "error"}}
    responses.add(responses.POST, url, json=body, status=500)

    with pytest.raises(requests.HTTPError) as ex:
        atlas.save_transaction("test-slug", {"outcome": "Success"}, MockTransaction(), BINK_ASSIGNED)
    assert ex.value.response.status_code == 500


@responses.activate
def test_save_transaction_bad_400(atlas: Atlas) -> None:
    url = f"{TEST_ATLAS_URL}/transaction/save"
    body = {"bad_request": {"outcome": "error"}}
    responses.add(responses.POST, url, json=body, status=400)

    with pytest.raises(requests.HTTPError) as ex:
        atlas.save_transaction("test-slug", {"outcome": "Success"}, MockTransaction(), BINK_ASSIGNED)
    assert ex.value.response.status_code == 400
