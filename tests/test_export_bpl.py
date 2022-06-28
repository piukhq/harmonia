from hashlib import sha1
from unittest.mock import ANY

import pendulum
import responses
from app import encryption

import settings
from app.exports.agents.bpl import Asos
from app.exports.models import ExportTransaction
from app.feeds import FeedType
from app import db

settings.EUROPA_URL = "http://europa"
settings.VAULT_URL = "https://vault"

MOCK_URL = "http://iceland.test"


# export_transaction = ExportTransaction(
#     feed_type=FeedType.REFUND,
#     merchant_internal_id=None,
#     status=ExportTransactionStatus.PENDING,
#     id=4,
#     provider_slug='bpl-asos',
#     user_id=0,
#     settlement_key='07f4202a0fca3964ff0a84bbe1d442ec4a533f10be84b964896bf9068a3436aa',
#     transaction_date=datetime(2020, 10, 27, 15, 1, 59),
#     scheme_account_id=0,
#     last_four='7890',
#     created_at=datetime(2022, 6, 28, 9, 43, 36, 724438),
#     spend_amount=-8945,
#     payment_card_account_id=0,
#     expiry_month=None,
#     updated_at=None,
#     spend_currency='GBP',
#     credentials='6N5oDbI2qQk6IJgZWWvtNfJMdOzqa5scqUdeT6ri4tmyRmSn31LTQC/mrUpRTglY1IqrmXXzip9JkAtEW75+h01gfAs/nzAKRn9d5jUzRc/qFUj4zw/yw2odH95W5OivPrcGyhUId8h18SR8MK4O9ZL9tlSbFKE6OqHlTFo+9341b+Cmxs9lE9GLTh2EiA4W',
#     expiry_year=None,
#     loyalty_id='loyalty-123',
#     auth_code='444444',
#     payment_provider_slug='visa',
#     transaction_id='76b7408b-c750-48f9-a727-fbb33cad9531',
#     mid='test-mid-123',
#     approval_code='',
#     location_id=None,
#     pending_exports=[PendingExport(id=4, created_at=datetime(2022, 6, 28, 9, 44, 59, 909339), updated_at=None, provider_slug='bpl-asos', export_transaction_id=4, retry_count=0, retry_at=None)],
#     decrypted_credentials={'card_number': 'loyalty-123', 'merchant_identifier': '88899966', 'email': 'test-123@testbink.com'},
# )


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
        mid="test-mid-123",
        provider_slug="bpl-asos",
        transaction_date=pendulum.now().in_timezone("Europe/London"),
        spend_amount=5566,
        spend_currency="GBP",
        payment_card_account_id=1,
        feed_type=FeedType.AUTH,
        settlement_key=None,
        user_id=1,
        scheme_account_id=1,
        # credentials='6N5oDbI2qQk6IJgZWWvtNfJMdOzqa5scqUdeT6ri4tmyRmSn31LTQC/mrUpRTglY1IqrmXXzip9JkAtEW75+h01gfAs/nzAKRn9d5jUzRc/qFUj4zw/yw2odH95W5OivPrcGyhUId8h18SR8MK4O9ZL9tlSbFKE6OqHlTFo+9341b+Cmxs9lE9GLTh2EiA4W',
        credentials=encryption.encrypt_credentials({'card_number': 'loyalty-123', 'merchant_identifier': '88899966', 'email': 'test-123@testbink.com'})
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
    assert data['transaction_total'] == export_transaction.spend_amount
    assert data['datetime'] == export_transaction.transaction_date.int_timestamp
    assert data['MID'] == export_transaction.mid
    assert data['loyalty_id'] == '88899966'
    assert data['transaction_id'] == export_transaction.transaction_id
