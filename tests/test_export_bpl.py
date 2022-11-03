from hashlib import sha1

import pendulum
import responses

import settings
from app import db, encryption
from app.exports.agents.bpl import Asos
from app.exports.models import ExportTransaction
from app.feeds import FeedType

settings.EUROPA_URL = "http://europa"
settings.VAULT_URL = "https://vault"

MOCK_URL = "http://iceland.test"

primary_identifier = "test-mid-123"
secondary_identifier = "test-mid-456"


def add_mock_routes():
    responses.add(
        "GET",
        f"{settings.EUROPA_URL}/configuration",
        json={
            "merchant_url": f"{MOCK_URL}/",
            "integration_service": 0,
            "retry_limit": 100,
            "log_level": 0,
            "callback_url": f"{MOCK_URL}/callback",
            "country": "uk",
            "security_credentials": {
                "outbound": {"credentials": [{"storage_key": "test1"}]},
                "inbound": {"credentials": [{"storage_key": "test2"}]},
            },
        },
    )

    responses.add(
        "GET",
        f"{settings.VAULT_URL}/secrets/test1/",
        json={"id": "https://test5/a/b/c", "value": '{"data": {"value": "test3"}}'},
    )
    responses.add(
        "GET",
        f"{settings.VAULT_URL}/secrets/test2/",
        json={"id": "https://test6/a/b/c", "value": '{"data": {"value": "test4"}}'},
    )
    responses.add(
        "GET",
        f"{settings.VAULT_URL}/secrets/aes-keys/",
        json={"id": "http://test-123/a/b/c", "value": '{"AES_KEY": "value-123"}'},
    )


def create_export_transaction() -> ExportTransaction:
    return ExportTransaction(
        transaction_id="76b7408b-c750-48f9-a727-fbb33cad9531",
        loyalty_id="loyalty-123",
        mid=secondary_identifier,
        provider_slug="bpl-asos",
        transaction_date=pendulum.now().in_timezone("Europe/London"),
        spend_amount=5566,
        spend_currency="GBP",
        payment_card_account_id=1,
        feed_type=FeedType.AUTH,
        settlement_key=None,
        user_id=1,
        scheme_account_id=1,
        credentials=encryption.encrypt_credentials(
            {"card_number": "loyalty-123", "merchant_identifier": "88899966", "email": "test-123@testbink.com"}
        ),
        primary_identifier=primary_identifier,
    )


@responses.activate
def test_export_transaction_id():
    add_mock_routes()
    export_transaction = create_export_transaction()
    transaction_datetime = export_transaction.transaction_date.int_timestamp
    asos = Asos()
    result = asos.export_transaction_id(export_transaction, transaction_datetime)

    assert (
        result
        == asos.provider_slug
        + "-"
        + sha1((export_transaction.transaction_id + str(transaction_datetime)).encode()).hexdigest()
    )


@responses.activate
def test_export_transaction_id_refund_amount():
    add_mock_routes()
    export_transaction = create_export_transaction()
    export_transaction.feed_type = FeedType.REFUND
    export_transaction.spend_amount = -5566
    transaction_datetime = export_transaction.transaction_date.int_timestamp
    asos = Asos()
    result = asos.export_transaction_id(export_transaction, transaction_datetime)

    assert (
        result
        == asos.provider_slug
        + "-"
        + sha1((f"{export_transaction.transaction_id}-refund" + str(transaction_datetime)).encode()).hexdigest()
    )


@responses.activate
def test_make_export_data(db_session: db.Session):
    add_mock_routes()
    export_transaction = create_export_transaction()
    asos = Asos()
    result = asos.make_export_data(export_transaction, db_session)
    data = result.outputs[0].data
    assert "bpl-asos-" in data["id"]
    assert data["transaction_total"] == export_transaction.spend_amount
    assert data["datetime"] == export_transaction.transaction_date.int_timestamp
    assert data["MID"] == primary_identifier
    assert data["loyalty_id"] == "88899966"
    assert data["transaction_id"] == export_transaction.transaction_id
