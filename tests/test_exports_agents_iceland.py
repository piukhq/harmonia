import json
import logging
from unittest import mock

import pytest
import responses
from soteria.configuration import Configuration

import settings
from app import db, encryption, models
from app.exports.agents.iceland import Iceland, hash_ids
from tests.fixtures import Default, get_or_create_export_transaction, get_or_create_pending_export

settings.EUROPA_URL = "http://europa"
settings.VAULT_URL = "https://vault"
settings.DEBUG = False

MOCK_URL = "http://iceland.test"
TOKEN_URL = "http://token.test"

MERCHANT_SLUG = "iceland-bonus-card"
MID = Default.primary_mids


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
                "outbound": {
                    "service": Configuration.OAUTH_SECURITY,
                    "credentials": [
                        {"storage_key": "test1", "credential_type": "compound_key"},
                    ],
                },
                "inbound": {
                    "service": Configuration.OPEN_AUTH_SECURITY,
                    "credentials": [
                        {"storage_key": "test2", "credential_type": "compound_key"},
                    ],
                },
            },
        },
    )

    responses.add(
        "GET",
        f"{settings.VAULT_URL}/secrets/test1/",
        json={
            "id": "https://test5/a/b/c",
            "value": '{"data": {"value": {"payload": {"client_id": "a_client_id", "client_secret": "a_client_secret", '
            '"grant_type": "client_credentials", "resource": "a_resource"}, "prefix": "Bearer", '
            '"url": "http://token.test/"}}}',
        },
    )
    responses.add(
        "GET",
        f"{settings.VAULT_URL}/secrets/test2/",
        json={"id": "https://test6/a/b/c", "value": '{"data": {"value": "test4"}}'},
    )


@pytest.fixture
@responses.activate
def iceland() -> Iceland:
    add_mock_routes()
    return Iceland()


@pytest.fixture
def export_transaction(db_session: db.Session) -> models.ExportTransaction:
    return get_or_create_export_transaction(
        session=db_session,
        provider_slug=MERCHANT_SLUG,
        mid=MID,
        primary_identifier=MID,
    )


@pytest.fixture
def pending_export(export_transaction: models.ExportTransaction, db_session: db.Session) -> models.PendingExport:
    return get_or_create_pending_export(
        session=db_session, export_transaction=export_transaction, provider_slug=MERCHANT_SLUG
    )


def drop_export_transaction(db_session: db.Session, export_transaction: models.ExportTransaction) -> None:
    drop_export_transaction_constraints = "ALTER TABLE export_transaction DISABLE TRIGGER ALL"
    db_session.execute(drop_export_transaction_constraints)
    db_session.delete(export_transaction)
    db_session.commit()


class Expected:
    formatted_transaction = [
        {
            "record_uid": "voydgerxzp4k97w0pn0q2lo183j5mvjx",
            "merchant_scheme_id1": "vryp7xv4l2ejg36p0nmk1qd0z5o89rlp",
            "merchant_scheme_id2": 10,
            "transaction_id": 1,
        },
        {
            "record_uid": "voydgerxzp4k97w0pn0q2lo183j5mvjx",
            "merchant_scheme_id1": "vryp7xv4l2ejg36p0nmk1qd0z5o89rlp",
            "merchant_scheme_id2": 20,
            "transaction_id": 2,
        },
    ]


class MockExportTransaction:
    def __init__(self, transaction_id, scheme_account_id, user_id, merchant_identifier):
        self.transaction_id = transaction_id
        mock_credentials = {"card_number": "loyalty-123", "merchant_identifier": merchant_identifier}
        self.credentials = encryption.encrypt_credentials(mock_credentials)
        self.mid = "1234567"
        self.user_id = user_id
        self.scheme_account_id = scheme_account_id
        self.loyalty_id = merchant_identifier

    @property
    def decrypted_credentials(self):
        return encryption.decrypt_credentials(self.credentials)


def test_get_loyalty_identifier(iceland: Iceland, export_transaction: models.ExportTransaction) -> None:
    loyalty_identifier = iceland.get_loyalty_identifier(export_transaction)

    assert loyalty_identifier == Default.loyalty_id


def test_get_record_uid(iceland: Iceland, export_transaction: models.ExportTransaction) -> None:
    record_uuid = iceland.get_record_uid(export_transaction)

    assert record_uuid == hash_ids.encode(export_transaction.scheme_account_id)


def test_format_transactions(iceland: Iceland) -> None:
    transactions = [MockExportTransaction(1, 2, 3, 10), MockExportTransaction(2, 2, 3, 20)]

    formatted_transaction = iceland.format_transactions(transactions)

    assert formatted_transaction == Expected.formatted_transaction


@responses.activate
def test_make_secured_request(iceland: Iceland) -> None:
    responses.add(
        "POST",
        "http://token.test/",
        json={"access_token": "a_token"},
    )
    body = {
        "message_uid": "c3cb6bf3-46a2-4d2c-a77c-e06ac9981f0f",
        "transactions": [
            {
                "record_uid": "v8vzj4ykl7g28d6mln9x05m31qpeor27",
                "merchant_scheme_id1": "v8vzj4ykl7g28d6mln9x05m31qpeor27",
                "merchant_scheme_id2": "88899966",
                "transaction_id": "42dff164-552b-4e9b-91b7-8b637b2a1a88",
            }
        ],
    }
    secured_request = iceland.make_secured_request(json.dumps(body))

    assert secured_request == {
        "json": body,
        "headers": {"Authorization": "Bearer a_token"},
    }


def test_make_export_data(iceland: Iceland, export_transaction: models.ExportTransaction) -> None:
    result = iceland._make_export_data(transactions=[export_transaction], index=0)
    export_data = json.loads(result.outputs[0].data)

    assert export_data == {
        "message_uid": mock.ANY,
        "transactions": [
            {
                "record_uid": hash_ids.encode(export_transaction.scheme_account_id),
                "merchant_scheme_id1": hash_ids.encode(export_transaction.user_id),
                "merchant_scheme_id2": Default.loyalty_id,
                "transaction_id": Default.transaction_id,
            }
        ],
    }


def test_yield_export_data(
    iceland: Iceland, export_transaction: models.ExportTransaction, db_session: db.Session
) -> None:
    export_data_generator = iceland.yield_export_data([export_transaction], session=db_session)
    data = json.loads(next(export_data_generator).outputs[0].data)

    assert data == {
        "message_uid": mock.ANY,
        "transactions": [
            {
                "record_uid": hash_ids.encode(export_transaction.scheme_account_id),
                "merchant_scheme_id1": hash_ids.encode(export_transaction.user_id),
                "merchant_scheme_id2": Default.loyalty_id,
                "transaction_id": Default.transaction_id,
            }
        ],
    }


@mock.patch("app.db.run_query")
@mock.patch.object(Iceland, "_save_export_transactions")
@mock.patch("app.service.atlas.queue_audit_message")
@mock.patch.object(Iceland, "send_export_data")
@mock.patch.object(Iceland, "_update_metrics")
def test_export_all(
    mock_update_metrics,
    mock_send_export_data,
    mock_queue_audit_message,
    mock_save_export_transactions,
    mock_run_query,
    iceland: Iceland,
    export_transaction: models.ExportTransaction,
    pending_export: models.PendingExport,
    db_session: db.Session,
) -> None:
    audit_message = {"audit_data": "some_audit_data"}
    mock_send_export_data.return_value = audit_message

    iceland.export_all(session=db_session)

    assert mock_update_metrics.call_args.args[0].transactions[0] == export_transaction
    assert mock_send_export_data.call_args.args[0].transactions[0] == export_transaction
    assert mock_queue_audit_message.call_args.args[0] == audit_message
    assert mock_save_export_transactions.call_args.args[0].transactions[0] == export_transaction


def test_export_all_no_transactions(
    iceland: Iceland,
    export_transaction: models.ExportTransaction,
    db_session: db.Session,
) -> None:
    drop_export_transaction(db_session, export_transaction)
    result = iceland.export_all(session=db_session)

    assert result is None


@mock.patch.object(Iceland, "_save_export_transactions")
@mock.patch("app.service.atlas.queue_audit_message")
@mock.patch.object(Iceland, "send_export_data")
@mock.patch.object(Iceland, "_update_metrics")
def test_export_all_pending_transaction_deleted(
    mock_update_metrics,
    mock_send_export_data,
    mock_queue_audit_message,
    mock_save_export_transactions,
    iceland: Iceland,
    pending_export: models.PendingExport,
    db_session: db.Session,
    caplog,
) -> None:
    caplog.set_level(logging.DEBUG)
    iceland.log.propagate = True

    assert db_session.query(models.PendingExport).one_or_none() == pending_export

    iceland.export_all(session=db_session)

    assert "Exporting 1 transactions." in caplog.messages
    assert "Deleted 1 pending exports." in caplog.messages
    assert db_session.query(models.PendingExport).one_or_none() is None


@responses.activate
@mock.patch("app.exports.agents.iceland.atlas")
def test_send_export_data(
    mock_atlas, iceland: Iceland, export_transaction: models.ExportTransaction, db_session: db.Session
) -> None:
    responses.add(
        "POST",
        "http://token.test/",
        json={"access_token": "a_token"},
    )
    response_body = {"body": "", "status_code": 204, "timestamp": "2022-11-24 10:00:00"}
    responses.add(
        responses.POST,
        url=MOCK_URL,
        json=response_body,
        status=204,
    )
    export_data = iceland._make_export_data(transactions=[export_transaction], index=0)
    transactions = iceland.format_transactions([export_transaction])
    iceland.send_export_data(export_data, session=db_session)

    # Post to Iceland
    responses.assert_call_count(TOKEN_URL, 1)
    responses.assert_call_count(MOCK_URL, 1)
    assert responses.calls[1].request.headers["Authorization"] == "Bearer a_token"
    assert json.loads(responses.calls[1].request.body)["transactions"] == transactions

    # Post to Atlas
    assert mock_atlas.make_audit_transactions.call_args.args[0] == [export_transaction]
    assert mock_atlas.make_audit_message.call_args.args == (MERCHANT_SLUG, mock_atlas.make_audit_transactions())
    assert json.loads(mock_atlas.make_audit_message.call_args.kwargs["request"]) == {
        "message_uid": mock.ANY,
        "transactions": transactions,
    }
    assert json.loads(mock_atlas.make_audit_message.call_args.kwargs["response"]._content) == response_body
