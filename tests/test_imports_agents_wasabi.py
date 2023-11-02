import logging
from pathlib import PosixPath
from unittest import mock

import pendulum
import pytest
import responses
from soteria.configuration import Configuration

import settings
from app import db
from app.imports.agents.wasabi import Wasabi
from app.prometheus import BinkPrometheus
from app.service.hermes import PaymentProviderSlug

settings.EUROPA_URL = "http://europa"
settings.VAULT_URL = "https://vault"

MOCK_URL = "http://wasabi.test"
MERCHANT_SLUG = "wasabi-club"


def add_mock_routes():
    responses.add(
        "GET",
        f"{settings.EUROPA_URL}/configuration",
        json={
            "merchant_url": f"{MOCK_URL}/",
            "integration_service": Configuration.TRANSACTION_MATCHING,
            "retry_limit": 0,
            "log_level": Configuration.DEBUG_LOG_LEVEL,
            "callback_url": None,
            "country": "uk",
            "security_credentials": {
                "outbound": {
                    "service": Configuration.OPEN_AUTH_SECURITY,
                    "credentials": [],
                },
                "inbound": {
                    "service": Configuration.RSA_SECURITY,
                    "credentials": [
                        {"storage_key": "test_inbound_compound_key", "credential_type": "compound_key"},
                        {"storage_key": "test_inbound_bink_private_key", "credential_type": "bink_private_key"},
                    ],
                },
            },
        },
    )

    responses.add(
        "GET",
        f"{settings.VAULT_URL}/secrets/test_inbound_compound_key/",
        json={"value": '{"data": {"host": "host.bink.com", "port": "900", "username": "test_username"}}'},
    )
    responses.add(
        "GET", f"{settings.VAULT_URL}/secrets/test_inbound_bink_private_key/", json={"value": '{"data": {"value": ""}}'}
    )


TRANSACTION_DATA = {
    "Store No_": "A076",
    "Entry No_": "16277",
    "Transaction No_": "123456789",
    "Tender Type": "3",
    "Amount": "12.22",
    "Card Number": "123456******7890",
    "Card Type Name": "American Express",
    "Auth_code": "666666",
    "Authorisation Ok": "1",
    "Date": "27/10/2020",
    "Time": "15:01:59",
    "EFT Merchant No_": "test-mid-123",
    "Receipt No_": "0000A00982528005882",
}


@responses.activate
def test_security_credentials() -> None:
    add_mock_routes()

    assert Wasabi()._security_credentials == {
        "compound_key": {"host": "host.bink.com", "port": "900", "username": "test_username"},
        "bink_private_key": {"value": ""},
    }


@responses.activate
def test_sftp_credentials() -> None:
    add_mock_routes()

    assert Wasabi().sftp_credentials._asdict() == {
        "host": "host.bink.com",
        "port": "900",
        "username": "test_username",
        "password": None,
    }


@responses.activate
def test_skey_returns_expected_value() -> None:
    add_mock_routes()

    assert Wasabi().skey == {"value": ""}


@responses.activate
def test_filesource_returns_correct_object(db_session: db.Session) -> None:
    add_mock_routes()
    with mock.patch("app.imports.agents.bases.file_agent.db.session_scope", return_value=db_session):
        filename = Wasabi().filesource

    assert filename.path == PosixPath("/")
    assert type(filename.log) == logging.Logger
    assert filename.log.name == "sftp-file-source"
    assert type(filename.bink_prometheus) == BinkPrometheus
    assert filename.credentials._asdict() == {
        "host": "host.bink.com",
        "port": "900",
        "username": "test_username",
        "password": None,
    }
    assert filename.skey == {"value": ""}
    assert type(filename.provider_agent) == Wasabi
    assert filename.archive_path == "archive"


def test_yield_transactions_data() -> None:
    transaction = (
        b"Store No_,Entry No_,Transaction No_,Tender Type,Amount,Card Number,Card Type Name,Auth_code,"
        b"Authorisation Ok,Date,Time,EFT Merchant No_,Receipt No_\r\nA076,16277,123456789,3,12.22,"
        b"123456******7890,American Express,666666,1,27/10/2020,15:01:59,test-mid-123,0000A00982528005882\r\n"
    )
    generator = Wasabi().yield_transactions_data(transaction)

    assert next(generator) == TRANSACTION_DATA


def test_yield_transactions_data_auth_code_is_decline() -> None:
    transaction = (
        b"Store No_,Entry No_,Transaction No_,Tender Type,Amount,Card Number,Card Type Name,Auth_code,"
        b"Authorisation Ok,Date,Time,EFT Merchant No_,Receipt No_\r\nA076,16277,123456789,3,12.22,"
        b"123456******7890,Another Provider,666666,1,27/10/2020,15:01:59,test-mid-123,0000A00982528005882\r\n"
    )
    generator = Wasabi().yield_transactions_data(transaction)

    with pytest.raises(StopIteration):
        next(generator)


def test_to_transaction_fields() -> None:
    scheme_transaction_fields = Wasabi().to_transaction_fields(TRANSACTION_DATA)
    assert len(scheme_transaction_fields) == 1
    assert scheme_transaction_fields[0]._asdict() == {
        "merchant_slug": MERCHANT_SLUG,
        "payment_provider_slug": PaymentProviderSlug.AMEX,
        "transaction_date": pendulum.DateTime(2020, 10, 27, 15, 1, 59, tzinfo=pendulum.timezone("Europe/London")),
        "has_time": True,
        "spend_amount": 1222,
        "spend_multiplier": 100,
        "spend_currency": "GBP",
        "first_six": "123456",
        "last_four": "7890",
        "auth_code": "666666",
        "extra_fields": None,
    }


def test_get_transaction_id() -> None:
    transaction_id = Wasabi().get_transaction_id(TRANSACTION_DATA)
    assert transaction_id == "0000A00982528005882"


def test_get_transaction_date() -> None:
    transaction_date = Wasabi().get_transaction_date(TRANSACTION_DATA)
    assert transaction_date == pendulum.DateTime(2020, 10, 27, 15, 1, 59, tzinfo=pendulum.timezone("Europe/London"))
