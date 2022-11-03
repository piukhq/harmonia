from unittest import mock

import pendulum

from app import db, models
from app.exports.agents import AgentExportData, AgentExportDataOutput
from app.exports.agents.squaremeal import SquareMeal
from app.feeds import FeedType

transaction_id = "1234567"
primary_identifier = "test-mid-primary"
secondary_identifier = "test-mid-secondary"
transaction_date = pendulum.DateTime(2022, 11, 1, 17, 14, 8, 838138, tzinfo=pendulum.timezone("Europe/London"))
settlement_key = "123456"
loyalty_id = 10
loyalty_slug = "squaremeal"

request_body = {
    "transaction_id": "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92",
    "loyalty_id": loyalty_id,
    "auth": True,
    "cleared": False,
    "mid": primary_identifier,
    "transaction_date": transaction_date.format("YYYY-MM-DDTHH:mm:ss"),
    "transaction_amount": 5566,
    "transaction_currency": "GBP",
    "payment_card_account_id": 1,
    "store_id": None,
    "brand_id": None,
    "payment_card_last_four": None,
    "payment_scheme": {"slug": None, "auth_code": None, "approval_code": None},
    "payment_card_expiry_month": None,
    "payment_card_expiry_year": None,
}
response_body = {
    "body": "Bink Transaction details processed sucessfully!",
    "status_code": 200,
    "timestamp": "2022-11-02 16:36:45",
}


# TODO once fixture file is created, move
def create_transaction_record(db_session: db.Session):
    transaction = db.get_or_create(
        models.Transaction,
        transaction_id=transaction_id,
        defaults=dict(
            payment_provider_slug="amex",
            feed_type=FeedType.AUTH,
            status="IMPORTED",
            merchant_identifier_ids=[1],
            merchant_slug=loyalty_slug,
            settlement_key=settlement_key,
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
            primary_identifier=primary_identifier,
        ),
        session=db_session,
    )
    return transaction


# TODO once fixture file is created, move and make args more descriptive
def create_export_transaction(txn_id, loy_id, set_key) -> models.ExportTransaction:
    exp_txn = models.ExportTransaction(
        transaction_id=txn_id,
        loyalty_id=loy_id,
        mid=secondary_identifier,
        provider_slug=loyalty_slug,
        transaction_date=transaction_date,
        spend_amount=5566,
        spend_currency="GBP",
        payment_card_account_id=1,
        feed_type=FeedType.AUTH,
        settlement_key=set_key,
        user_id=1,
        scheme_account_id=1,
        credentials="something",
        primary_identifier=primary_identifier,
    )
    return exp_txn


def test_get_settlement_key_without_settlement_key(db_session: db.Session) -> None:
    create_transaction_record(db_session)
    exp_txn = create_export_transaction(transaction_id, loyalty_id, None)
    expected_settlement_key = settlement_key
    squaremeal = SquareMeal()
    result_settlement_key = squaremeal.get_settlement_key(exp_txn, db_session)

    assert result_settlement_key == expected_settlement_key


def test_get_settlement_key_with_settlement_key(db_session: db.Session) -> None:
    create_transaction_record(db_session)
    exp_txn = create_export_transaction(transaction_id, loyalty_id, settlement_key)
    expected_settlement_key = settlement_key
    squaremeal = SquareMeal()
    result_settlement_key = squaremeal.get_settlement_key(exp_txn, db_session)

    assert result_settlement_key == expected_settlement_key


def test_make_export_data(db_session: db.Session) -> None:
    exp_txn = create_export_transaction(transaction_id, loyalty_id, settlement_key)
    squaremeal = SquareMeal()

    expected_result = AgentExportData(
        outputs=[
            AgentExportDataOutput(
                key="export.json",
                data=request_body,
            )
        ],
        transactions=[exp_txn],
        extra_data={},
    )
    result = squaremeal.make_export_data(exp_txn, db_session)

    assert result == expected_result


@mock.patch("app.exports.agents.squaremeal.atlas")
@mock.patch("app.service.squaremeal.SquareMeal.transactions", return_value=response_body)
def test_export(mock_squaremeal_post, mock_atlas, db_session: db.Session) -> None:
    exp_txn = create_export_transaction(transaction_id, loyalty_id, settlement_key)
    squaremeal = SquareMeal()
    export_data = squaremeal.make_export_data(exp_txn, db_session)

    squaremeal.export(export_data, session=db_session)

    # Post to Squaremeal
    mock_squaremeal_post.assert_called_once_with(request_body, "/api/BinkTransactions")

    # Post to Atlas
    assert mock_atlas.make_audit_transactions.call_args.args[0] == [exp_txn]
    assert mock_atlas.make_audit_message.call_args.args == (loyalty_slug, mock_atlas.make_audit_transactions())
    assert mock_atlas.make_audit_message.call_args.kwargs == {
        "request": request_body,
        "request_timestamp": mock.ANY,
        "response": response_body,
        "response_timestamp": mock.ANY,
        "request_url": "https://uk-bink-transactions-dev.azurewebsites.net/api/BinkTransactions",
    }
    assert mock_atlas.queue_audit_message.call_count == 1
