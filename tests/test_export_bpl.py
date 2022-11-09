from hashlib import sha1

from app import db
from app.exports.agents.bpl import Asos
from app.exports.models import ExportTransaction
from app.feeds import FeedType
from tests.fixtures import Default, create_export_transaction

primary_identifier = Default.primary_identifier
secondary_identifier = Default.secondary_identifier


def create_export_transaction_object() -> ExportTransaction:
    return create_export_transaction(
        transaction_id="76b7408b-c750-48f9-a727-fbb33cad9531",
        provider_slug="bpl-asos",
        mid=secondary_identifier,
        payment_card_account_id=1,
        feed_type=FeedType.AUTH,
        settlement_key=None,
    )


def test_export_transaction_id():
    export_transaction = create_export_transaction_object()
    transaction_datetime = export_transaction.transaction_date.int_timestamp
    asos = Asos()
    result = asos.export_transaction_id(export_transaction, transaction_datetime)

    assert (
        result
        == asos.provider_slug
        + "-"
        + sha1((export_transaction.transaction_id + str(transaction_datetime)).encode()).hexdigest()
    )


def test_export_transaction_id_refund_amount():
    export_transaction = create_export_transaction_object()
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


def test_make_export_data(db_session: db.Session):
    export_transaction = create_export_transaction_object()
    asos = Asos()
    result = asos.make_export_data(export_transaction, db_session)
    data = result.outputs[0].data
    assert "bpl-asos-" in data["id"]
    assert data["transaction_total"] == export_transaction.spend_amount
    assert data["datetime"] == export_transaction.transaction_date.int_timestamp
    assert data["MID"] == primary_identifier
    assert data["loyalty_id"] == primary_identifier
    assert data["transaction_id"] == export_transaction.transaction_id
