import pendulum
import pytest
import responses

from app import db, models
from app.exports.agents.squaremeal import SquareMeal
from app.exports.exceptions import MissingExportData
from app.feeds import FeedType


def create_transaction_record(db_session: db.Session):
    transaction = db.get_or_create(
        models.Transaction,
        transaction_id="1234567",
        defaults=dict(
            payment_provider_slug="amex",
            feed_type=FeedType.AUTH,
            status="IMPORTED",
            merchant_identifier_ids=[1],
            merchant_slug="squaremeal",
            settlement_key="123456",
            match_group="98765",
            transaction_date=pendulum.now(),
            has_time=True,
            spend_amount=5566,
            spend_multiplier=1,
            spend_currency="GBR",
            card_token="9876543",
            first_six="666666",
            last_four="4444",
            auth_code="666655",
        ),
        session=db_session,
    )
    return transaction


def create_export_transaction(transaction_id, merchant_identifier, settlement_key) -> models.ExportTransaction:
    exp_txn = models.ExportTransaction(
        transaction_id=transaction_id,
        loyalty_id=merchant_identifier,
        mid="1234567",
        provider_slug="squaremeal",
        transaction_date=pendulum.now().in_timezone("Europe/London"),
        spend_amount=5566,
        spend_currency="GBP",
        payment_card_account_id=1,
        feed_type=FeedType.AUTH,
        settlement_key=None,
        user_id=1,
        scheme_account_id=1,
        credentials="something",
    )
    return exp_txn


@responses.activate
def test_get_settlement_key_without_settlement_key(db_session: db.Session) -> None:
    create_transaction_record(db_session)
    exp_txn = create_export_transaction("1234567", 10, None)
    expected_settlement_key = "123456"
    squaremeal = SquareMeal()
    settlement_key = squaremeal.get_settlement_key(exp_txn, db_session)

    assert settlement_key == expected_settlement_key


@responses.activate
def test_get_settlement_key_with_settlement_key(db_session: db.Session) -> None:
    create_transaction_record(db_session)
    exp_txn = create_export_transaction("1234567", 10, "123456")
    expected_settlement_key = "123456"
    squaremeal = SquareMeal()
    settlement_key = squaremeal.get_settlement_key(exp_txn, db_session)

    assert settlement_key == expected_settlement_key


def test_export_transaction_is_valid():
    exp_txn = create_export_transaction("1234567", 10, "123456")
    exp_txn.merchant_internal_id = "9afcf26d-7d68-4baf-3847-8dc8a9e800ef"
    exp_txn.location_id = "9afcf26d-7d68-4baf-3847-8dc8a9e800ef"

    squaremeal = SquareMeal()
    result = squaremeal._export_transaction_is_valid(exp_txn)

    assert result is True


def test_export_transaction_is_valid_missing_merchant_internal_id():
    exp_txn = create_export_transaction("1234567", 10, "123456")
    exp_txn.location_id = "9afcf26d-7d68-4baf-3847-8dc8a9e800ef"

    squaremeal = SquareMeal()
    result = squaremeal._export_transaction_is_valid(exp_txn)

    assert result is False


def test_export_transaction_is_valid_missing_location_id():
    exp_txn = create_export_transaction("1234567", 10, "123456")
    exp_txn.merchant_internal_id = "9afcf26d-7d68-4baf-3847-8dc8a9e800ef"

    squaremeal = SquareMeal()
    result = squaremeal._export_transaction_is_valid(exp_txn)

    assert result is False


def test_make_export_data(db_session: db.Session):
    exp_txn = create_export_transaction("1234567", 10, "123456")
    squaremeal = SquareMeal()

    with pytest.raises(MissingExportData):
        squaremeal.make_export_data(exp_txn, db_session)
