import logging
from unittest import mock

import pendulum
import pytest
import responses

import settings
from app import db, encryption, models
from app.exports.agents.stonegate_unmatched import StonegateUnmatched
from tests.fixtures import Default, get_or_create_export_transaction, get_or_create_pending_export

settings.EUROPA_URL = "http://europa"
settings.VAULT_URL = "https://vault"
settings.DEBUG = False


MERCHANT_SLUG = "stonegate-unmatched"
MID = Default.primary_mids[0]


@pytest.fixture
@responses.activate
def stonegate_unmatched() -> StonegateUnmatched:
    return StonegateUnmatched()


@pytest.fixture
def export_transaction(db_session: db.Session) -> models.ExportTransaction:
    return get_or_create_export_transaction(
        session=db_session,
        provider_slug=MERCHANT_SLUG,
        mid=MID,
        primary_identifier=MID,
        transaction_date="2024-03-25T16:54:33+00:00",
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
    csv_transactions = "transaction_id,member_number,retailer_location_id,transaction_amount,transaction_date\r\n1,test_loyalty_id,123456,300,2024-03-25 16:54:33\r\n"  # noqa


class MockExportTransaction:
    def __init__(self, transaction_id, transaction_date, spend_amount, merchant_identifier, location_id):
        self.transaction_id = transaction_id
        mock_credentials = {"card_number": "loyalty-123", "merchant_identifier": merchant_identifier}
        self.credentials = encryption.encrypt_credentials(mock_credentials)
        self.mid = "1234567"
        self.spend_amount = spend_amount
        self.transaction_date = transaction_date
        self.loyalty_id = merchant_identifier
        self.location_id = location_id

    @property
    def decrypted_credentials(self):
        return encryption.decrypt_credentials(self.credentials)


def test_get_loyalty_identifier(
    stonegate_unmatched: StonegateUnmatched, export_transaction: models.ExportTransaction
) -> None:
    loyalty_identifier = stonegate_unmatched.get_loyalty_identifier(export_transaction)

    assert loyalty_identifier == Default.loyalty_id


def test_format_transactions(stonegate_unmatched: StonegateUnmatched) -> None:
    transactions = [
        MockExportTransaction(
            1, pendulum.datetime(2024, 3, 25, 16, 54, 33).format("YYYY-MM-DD HH:mm:ss"), 300, "test_loyalty_id", 123456
        ),
    ]

    csv_transactions = stonegate_unmatched.csv_transactions(transactions)

    assert csv_transactions == Expected.csv_transactions


def test_make_export_data(
    stonegate_unmatched: StonegateUnmatched, export_transaction: models.ExportTransaction
) -> None:
    result = stonegate_unmatched._make_export_data(transactions=[export_transaction])
    export_data = result.outputs[0].data

    assert (
        export_data
        == "transaction_id,member_number,retailer_location_id,transaction_amount,transaction_date\r\ndb0b14a3-0ca8-4281-9a77-57b5b88ec0a4,test_loyalty_id,,5566,2024-03-25 16:54:33\r\n"  # noqa
    )


def test_yield_export_data(
    stonegate_unmatched: StonegateUnmatched, export_transaction: models.ExportTransaction, db_session: db.Session
) -> None:
    export_data_generator = stonegate_unmatched.yield_export_data([export_transaction], session=db_session)
    data = next(export_data_generator).outputs[0].data

    assert (
        data
        == "transaction_id,member_number,retailer_location_id,transaction_amount,transaction_date\r\ndb0b14a3-0ca8-4281-9a77-57b5b88ec0a4,test_loyalty_id,,5566,2024-03-25 16:54:33\r\n"  # noqa
    )


@mock.patch("app.db.run_query")
@mock.patch.object(StonegateUnmatched, "_save_export_transactions")
@mock.patch("app.service.atlas.queue_audit_message")
@mock.patch.object(StonegateUnmatched, "send_export_data")
@mock.patch.object(StonegateUnmatched, "_update_metrics")
def test_export_all(
    mock_update_metrics,
    mock_send_export_data,
    mock_queue_audit_message,
    mock_save_export_transactions,
    mock_run_query,
    stonegate_unmatched: StonegateUnmatched,
    export_transaction: models.ExportTransaction,
    pending_export: models.PendingExport,
    db_session: db.Session,
) -> None:
    audit_message = {"audit_data": "some_audit_data"}
    mock_send_export_data.return_value = audit_message

    stonegate_unmatched.export_all(session=db_session)

    assert mock_update_metrics.call_args.args[0].transactions[0] == export_transaction
    assert mock_send_export_data.call_args.args[0].transactions[0] == export_transaction
    assert mock_queue_audit_message.call_args.args[0] == audit_message
    assert mock_save_export_transactions.call_args.args[0].transactions[0] == export_transaction


def test_export_all_no_transactions(
    stonegate_unmatched: StonegateUnmatched,
    export_transaction: models.ExportTransaction,
    db_session: db.Session,
) -> None:
    drop_export_transaction(db_session, export_transaction)
    result = stonegate_unmatched.export_all(session=db_session)

    assert result is None


@mock.patch.object(StonegateUnmatched, "_save_export_transactions")
@mock.patch("app.service.atlas.queue_audit_message")
@mock.patch.object(StonegateUnmatched, "send_export_data")
@mock.patch.object(StonegateUnmatched, "_update_metrics")
def test_export_all_pending_transaction_deleted(
    mock_update_metrics,
    mock_send_export_data,
    mock_queue_audit_message,
    mock_save_export_transactions,
    stonegate_unmatched: StonegateUnmatched,
    pending_export: models.PendingExport,
    db_session: db.Session,
    caplog,
) -> None:
    caplog.set_level(logging.DEBUG)
    stonegate_unmatched.log.propagate = True

    assert db_session.query(models.PendingExport).one_or_none() == pending_export

    stonegate_unmatched.export_all(session=db_session)

    assert "Exporting 1 transactions." in caplog.messages
    assert "Deleted 1 pending exports." in caplog.messages
    assert db_session.query(models.PendingExport).one_or_none() is None
