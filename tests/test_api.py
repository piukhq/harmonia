import pytest
from flask import Flask

import settings
from app.api import utils
from app.models import MerchantIdentifier

identifiers_json = {
    "identifiers": [
        {
            "identifier": "1111111111",
            "identifier_type": "PRIMARY",
            "location_id": None,
            "merchant_internal_id": " ",
            "loyalty_plan": "test-plan",
            "payment_scheme": "visa",
        },
        {
            "identifier": "1111111112",
            "identifier_type": "SECONDARY",
            "location_id": "34567654",
            "merchant_internal_id": "3456765",
            "loyalty_plan": "test-plan",
            "payment_scheme": "visa",
        },
        {
            "identifier": "1111111113",
            "identifier_type": "PSIMI",
            "location_id": "34567654",
            "merchant_internal_id": "3456765",
            "loyalty_plan": "test-plan",
            "payment_scheme": "visa",
        },
    ]
}


def test_expects_json():
    app = Flask(__name__)

    @app.route("/")
    @utils.expects_json
    def index():
        return "This should not pass!"

    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 415, resp.json


@pytest.fixture
def test_client():
    from app.api import auth

    # replace the requires_auth decorator with a no-op
    auth.auth_decorator = lambda: lambda *args, **kwargs: lambda fn: fn

    from app.api.app import create_app

    app = create_app()
    with app.test_request_context():
        yield app.test_client()


def test_post_identifiers(test_client, db_session):
    auth_headers = {"Authorization": "Token " + settings.SERVICE_API_KEY}

    resp = test_client.post("/txm/identifiers/", json=identifiers_json, headers=auth_headers)
    assert resp.status_code == 200, resp.json
    assert resp.json["onboarded"] == 3


def test_post_identifiers_blank_identifier_type(test_client, db_session):
    auth_headers = {"Authorization": "Token " + settings.SERVICE_API_KEY}
    missing_type_json = {
        "identifiers": [
            {
                "identifier": "1111111111",
                "identifier_type": "",
                "location_id": " ",
                "merchant_internal_id": " ",
                "loyalty_plan": "test_plan",
                "payment_scheme": "visa",
            },
            {
                "identifier": "1111111112",
                "identifier_type": "PRIMARY",
                "location_id": "34567654",
                "merchant_internal_id": "3456765",
                "loyalty_plan": "test_plan",
                "payment_scheme": "visa",
            },
        ]
    }
    resp = test_client.post("/txm/identifiers/", json=missing_type_json, headers=auth_headers)
    assert resp.status_code == 422, resp.json
    assert resp.json["title"] == "Validation error"


def test_post_identifiers_invalid_identifier_type(test_client, db_session):
    auth_headers = {"Authorization": "Token " + settings.SERVICE_API_KEY}
    not_type_json = {
        "identifiers": [
            {
                "identifier": "1111111111",
                "identifier_type": "banana",
                "location_id": " ",
                "merchant_internal_id": " ",
                "loyalty_plan": "test_plan",
                "payment_scheme": "visa",
            },
            {
                "identifier": "1111111112",
                "identifier_type": "PRIMARY",
                "location_id": "34567654",
                "merchant_internal_id": "3456765",
                "loyalty_plan": "test_plan",
                "payment_scheme": "visa",
            },
        ]
    }
    resp = test_client.post("/txm/identifiers/", json=not_type_json, headers=auth_headers)
    assert resp.status_code == 422, resp.json
    assert resp.json["title"] == "Validation error"


def test_post_identifiers_reject_duplicate_identifier(test_client, db_session):
    auth_headers = {"Authorization": "Token " + settings.SERVICE_API_KEY}
    identifiers_json_1 = {
        "identifiers": [
            {
                "identifier": "1111111111",
                "identifier_type": "PRIMARY",
                "location_id": " ",
                "merchant_internal_id": " ",
                "loyalty_plan": "test-plan",
                "payment_scheme": "visa",
            },
        ]
    }
    # First import of identifier
    resp = test_client.post("/txm/identifiers/", json=identifiers_json_1, headers=auth_headers)
    assert resp.status_code == 200, resp.json
    assert resp.json["onboarded"] == 1

    # Attempt to import the same identifier
    resp = test_client.post("/txm/identifiers/", json=identifiers_json_1, headers=auth_headers)
    assert resp.status_code == 200, resp.json
    assert resp.json["onboarded"] == 0


def test_post_identifiers_none_json(test_client, db_session):
    auth_headers = {"Authorization": "Token " + settings.SERVICE_API_KEY}

    resp = test_client.post("/txm/identifiers/", data="This is not json", headers=auth_headers)
    assert resp.status_code == 400, resp.json
    assert resp.json["title"] == "Bad request"


def test_delete_identifiers(test_client, db_session):
    auth_headers = {"Authorization": "Token " + settings.SERVICE_API_KEY}

    # Add some identifiers so that we can offboard (delete) them
    resp = test_client.post("/txm/identifiers/", json=identifiers_json, headers=auth_headers)
    assert resp.status_code == 200, resp.json
    assert resp.json["onboarded"] == 3

    # Delete 2 of the onboarded identifiers
    delete_json = {
        "identifiers": [
            {
                "identifier": "1111111111",
                "identifier_type": "PRIMARY",
                "payment_scheme": "visa",
            },
            {
                "identifier": "1111111112",
                "identifier_type": "SECONDARY",
                "payment_scheme": "visa",
            },
        ],
        "locations": [],
    }

    resp = test_client.post("/txm/identifiers/deletion", json=delete_json, headers=auth_headers)
    assert resp.status_code == 200, resp.json
    assert resp.json["deleted"] == 2

    assert db_session.query(MerchantIdentifier).count() == 1


def test_delete_blank_identifier_type(test_client, db_session):
    auth_headers = {"Authorization": "Token " + settings.SERVICE_API_KEY}

    # Add some identifiers, one with blank type, so that we can try to offboard (delete) them
    resp = test_client.post("/txm/identifiers/", json=identifiers_json, headers=auth_headers)
    assert resp.status_code == 200, resp.json
    assert resp.json["onboarded"] == 3

    # Delete 2 of the onboarded identifiers
    delete_json = {
        "identifiers": [
            {
                "identifier": "1111111111",
                "identifier_type": " ",
                "payment_scheme": "visa",
            },
            {
                "identifier": "1111111112",
                "identifier_type": "SECONDARY",
                "payment_scheme": "visa",
            },
        ],
        "locations": [],
    }

    resp = test_client.post("/txm/identifiers/deletion", json=delete_json, headers=auth_headers)
    assert resp.status_code == 422, resp.json
    assert resp.json["title"] == "Validation error"


def test_delete_identifiers_none_json(test_client, db_session):
    auth_headers = {"Authorization": "Token " + settings.SERVICE_API_KEY}

    resp = test_client.post("/txm/identifiers/deletion", data="This is not json", headers=auth_headers)
    assert resp.status_code == 400, resp.json
    assert resp.json["title"] == "Bad request"
