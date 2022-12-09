import json
from hashlib import sha1
from unittest import mock

import pendulum
import pytest
import responses

from app import db
from app.exports.agents.bpl import Asos, Bpl, Trenette
from app.exports.models import ExportTransaction
from app.feeds import FeedType
from tests.fixtures import Default, get_or_create_export_transaction

TRANSACTION_ID = "582228491099278"
TRANSACTION_DATE = pendulum.DateTime(2022, 10, 26, 17, 14, 8, 838138, tzinfo=pendulum.timezone("Europe/London"))
PRIMARY_IDENTIFIER = Default.primary_identifier
MERCHANT_SLUG = "bpl-trenette"
LOYALTY_ID = Default.loyalty_id
REQUEST_URL = "http://localhost/trenette/transaction"

REQUEST = {
    "MID": PRIMARY_IDENTIFIER,
    "datetime": mock.ANY,
    "id": mock.ANY,
    "loyalty_id": LOYALTY_ID,
    "transaction_id": TRANSACTION_ID,
    "transaction_total": 55.66,
}
RESPONSE = {"body": "Awarded", "status_code": 200, "timestamp": "2022-10-26 21:41:02"}


@pytest.fixture
def export_transaction() -> ExportTransaction:
    return get_or_create_export_transaction(
        transaction_id=TRANSACTION_ID,
        provider_slug=MERCHANT_SLUG,
        transaction_date=TRANSACTION_DATE,
        mid=Default.secondary_identifier,
        payment_card_account_id=1,
        feed_type=FeedType.AUTH,
        settlement_key=None,
    )


@mock.patch("app.exports.agents.bases.base.BaseAgent.provider_slug", return_value="bpl-trenette")
def test_merchant_name(mock_provider_slug) -> None:
    agent = Bpl()
    with pytest.raises(NotImplementedError) as e:
        agent.merchant_name
    assert e.value.args[0] == "Bpl is missing a required property: merchant_name"


def test_export_transaction_id(export_transaction: ExportTransaction) -> None:
    transaction_datetime = export_transaction.transaction_date.int_timestamp
    asos = Asos()
    result = asos.export_transaction_id(export_transaction, transaction_datetime)

    assert (
        result
        == asos.provider_slug
        + "-"
        + sha1((export_transaction.transaction_id + str(transaction_datetime)).encode()).hexdigest()
    )


def test_export_transaction_id_refund_amount(export_transaction: ExportTransaction) -> None:
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


def test_make_export_data(export_transaction: ExportTransaction, db_session: db.Session) -> None:
    asos = Asos()
    result = asos.make_export_data(export_transaction, db_session)
    export_data = result.outputs[0].data

    assert "bpl-asos-" in export_data["id"]
    assert export_data["transaction_total"] == export_transaction.spend_amount
    assert export_data["datetime"] == export_transaction.transaction_date.int_timestamp
    assert export_data["MID"] == PRIMARY_IDENTIFIER
    assert export_data["loyalty_id"] == LOYALTY_ID
    assert export_data["transaction_id"] == export_transaction.transaction_id


@responses.activate
@mock.patch("app.exports.agents.bpl.atlas")
@mock.patch("app.service.bpl.BplAPI.get_security_token", return_value="test_token")
def test_export_bpl(
    mock_get_security_token, mock_atlas, export_transaction: ExportTransaction, db_session: db.Session
) -> None:
    responses.add(responses.POST, url=REQUEST_URL, json=RESPONSE, status=200)
    agent = Trenette()
    export_data = agent.make_export_data(export_transaction, db_session)

    agent.export(export_data, session=db_session)

    # Post to BPL
    assert responses.calls[0].request.headers["Authorization"] == "Token test_token"
    assert responses.calls[0].request.url == "http://localhost/trenette/transaction"
    responses.assert_call_count("http://localhost/trenette/transaction", 1)
    assert json.loads(responses.calls[0].request.body) == REQUEST
    assert responses.calls[0].response.json() == RESPONSE


@responses.activate
@mock.patch("app.exports.agents.bpl.atlas")
@mock.patch("app.service.bpl.BplAPI.get_security_token", return_value="test_token")
def test_export_atlas(
    mock_get_security_token, mock_atlas, export_transaction: ExportTransaction, db_session: db.Session
) -> None:
    responses.add(responses.POST, url=REQUEST_URL, json=RESPONSE, status=200)
    agent = Trenette()
    export_data = agent.make_export_data(export_transaction, db_session)

    agent.export(export_data, session=db_session)

    # Post to Atlas
    assert mock_atlas.make_audit_transactions.call_args.args[0] == [export_transaction]
    assert mock_atlas.make_audit_message.call_args.args == (MERCHANT_SLUG, mock_atlas.make_audit_transactions())
    assert mock_atlas.make_audit_message.call_args.kwargs["request"] == REQUEST
    assert json.loads(mock_atlas.make_audit_message.call_args.kwargs["response"]._content) == RESPONSE
    assert mock_atlas.make_audit_message.call_args.kwargs["request_url"] == "http://localhost/trenette/transaction"
    assert mock_atlas.queue_audit_message.call_count == 1


@responses.activate
@mock.patch("app.exports.agents.bpl.atlas")
@mock.patch("app.service.bpl.BplAPI.get_security_token", return_value="test_token")
def test_export_exception_raised(
    mock_get_security_token, mock_atlas, export_transaction: ExportTransaction, db_session: db.Session
) -> None:
    responses.add(responses.POST, url=REQUEST_URL, json=RESPONSE, status=500)
    agent = Trenette()
    export_data = agent.make_export_data(export_transaction, db_session)

    with pytest.raises(Exception) as e:
        agent.export(export_data, session=db_session)
    assert e.value.args[0] == "BPL - bpl-trenette transaction endpoint returned 500"
