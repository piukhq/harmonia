from unittest import mock

import pendulum
import pytest

from app import db, models
from app.exports.agents import AgentExportData, AgentExportDataOutput
from app.exports.agents.squaremeal import SquareMeal
from app.feeds import FeedType
from tests.fixtures import Default, get_or_create_export_transaction, get_or_create_transaction

TRANSACTION_ID = "1234567"
PRIMARY_IDENTIFIER = Default.primary_identifier
SECONDARY_IDENTIFIER = Default.secondary_identifier
TRANSACTION_DATE = pendulum.DateTime(2022, 11, 1, 17, 14, 8, 838138, tzinfo=pendulum.timezone("Europe/London"))
SETTLEMENT_KEY = "123456"
LOYALTY_ID = "10"
MERCHANT_SLUG = "squaremeal"

REQUEST_BODY = {
    "transaction_id": "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92",
    "loyalty_id": LOYALTY_ID,
    "auth": True,
    "cleared": False,
    "mid": PRIMARY_IDENTIFIER,
    "transaction_date": TRANSACTION_DATE.format("YYYY-MM-DDTHH:mm:ss"),
    "transaction_amount": Default.spend_amount,
    "transaction_currency": Default.spend_currency,
    "payment_card_account_id": 1,
    "store_id": None,
    "brand_id": None,
    "payment_card_last_four": None,
    "payment_scheme": {"slug": None, "auth_code": None, "approval_code": None},
    "payment_card_expiry_month": None,
    "payment_card_expiry_year": None,
}
RESPONSE_BODY = {
    "body": "Bink Transaction details processed sucessfully!",
    "status_code": 200,
    "timestamp": "2022-11-02 16:36:45",
}


@pytest.fixture
def transaction(db_session: db.Session) -> None:
    get_or_create_transaction(
        session=db_session,
        transaction_id=TRANSACTION_ID,
        merchant_identifier_ids=[1],
        primary_identifier=PRIMARY_IDENTIFIER,
        merchant_slug=MERCHANT_SLUG,
        settlement_key=SETTLEMENT_KEY,
        card_token="9876543",
        first_six="666666",
        last_four="4444",
        auth_code="666655",
    )


@pytest.fixture
def export_transaction() -> models.ExportTransaction:
    return get_or_create_export_transaction(
        transaction_id=TRANSACTION_ID,
        provider_slug=MERCHANT_SLUG,
        transaction_date=TRANSACTION_DATE,
        loyalty_id=LOYALTY_ID,
        mid=SECONDARY_IDENTIFIER,
        primary_identifier=PRIMARY_IDENTIFIER,
        feed_type=FeedType.AUTH,
        settlement_key=SETTLEMENT_KEY,
        payment_card_account_id=1,
    )


def test_get_settlement_key_without_settlement_key(
    transaction: None, export_transaction: models.ExportTransaction, db_session: db.Session
) -> None:
    export_transaction.settlement_key = None
    squaremeal = SquareMeal()
    result_settlement_key = squaremeal.get_settlement_key(export_transaction, db_session)

    assert result_settlement_key == SETTLEMENT_KEY


def test_get_settlement_key_with_settlement_key(
    transaction: None, export_transaction: models.ExportTransaction, db_session: db.Session
) -> None:
    squaremeal = SquareMeal()
    result_settlement_key = squaremeal.get_settlement_key(export_transaction, db_session)

    assert result_settlement_key == SETTLEMENT_KEY


def test_make_export_data(export_transaction: models.ExportTransaction, db_session: db.Session) -> None:
    squaremeal = SquareMeal()

    expected_result = AgentExportData(
        outputs=[
            AgentExportDataOutput(
                key="export.json",
                data=REQUEST_BODY,
            )
        ],
        transactions=[export_transaction],
        extra_data={},
    )
    result = squaremeal.make_export_data(export_transaction, db_session)

    assert result == expected_result


@mock.patch("app.exports.agents.squaremeal.atlas")
@mock.patch("app.service.squaremeal.SquareMeal.transactions", return_value=RESPONSE_BODY)
def test_export(
    mock_squaremeal_post, mock_atlas, export_transaction: models.ExportTransaction, db_session: db.Session
) -> None:
    squaremeal = SquareMeal()
    export_data = squaremeal.make_export_data(export_transaction, db_session)

    squaremeal.export(export_data, session=db_session)

    # Post to Squaremeal
    mock_squaremeal_post.assert_called_once_with(REQUEST_BODY, "/api/BinkTransactions")

    # Post to Atlas
    assert mock_atlas.make_audit_transactions.call_args.args[0] == [export_transaction]
    assert mock_atlas.make_audit_message.call_args.args == (MERCHANT_SLUG, mock_atlas.make_audit_transactions())
    assert mock_atlas.make_audit_message.call_args.kwargs == {
        "request": REQUEST_BODY,
        "request_timestamp": mock.ANY,
        "response": RESPONSE_BODY,
        "response_timestamp": mock.ANY,
        "request_url": "https://uk-bink-transactions-dev.azurewebsites.net/api/BinkTransactions",
        "retry_count": 0,
    }
    assert mock_atlas.queue_audit_message.call_count == 1
