import json
from unittest import mock
from uuid import UUID

import pendulum
import pytest
import time_machine

from app import db
from app.feeds import FeedType
from app.imports.agents.bases.base import PaymentTransactionFields
from app.imports.agents.mastercard import MastercardAuth, MastercardTGX2Settlement, _make_settlement_key
from tests.fixtures import SampleTransactions, get_or_create_import_transaction, get_or_create_merchant_identifier

PAYMENT_PROVIDER_SLUG = "mastercard"

AUTH_TRANSACTION_1_ID = "NTI4QjdBN"
AUTH_TRANSACTION_1_DATE = pendulum.DateTime(2022, 10, 14, 13, 52, 24)
AUTH_TRANSACTION_1_MID = "test_primary_mid_1"
AUTH_TRANSACTION_1_TOKEN = "test_card_token_1"
AUTH_TRANSACTION_1 = SampleTransactions().mastercard_auth(
    amount=96,
    mid=AUTH_TRANSACTION_1_MID,
    payment_card_token=AUTH_TRANSACTION_1_TOKEN,
    third_party_id=AUTH_TRANSACTION_1_ID,
    time=AUTH_TRANSACTION_1_DATE,
)
AUTH_TRANSACTION_2 = SampleTransactions().mastercard_auth(
    amount=41,
    mid="test_primary_mid_2",
    payment_card_token="test_token_2",
    time=pendulum.DateTime(2022, 10, 14, 13, 54, 59),
)
# TODO - create fixture mastercard sample transaction for settlements
SETTLEMENT_TRANSACTION = {
    "record_type": "D",
    "mid": "test-mid-123",
    "location_id": "411111083",
    "aggregate_merchant_id": "664567",
    "amount": 1222,
    "date": "20201027",
    "time": "1501",
    "token": "token-123",
    "transaction_id": "48156a45-",
    "auth_code": "666666",
}
SETTLEMENT_TRANSACTION_EMPTY_PSIMI = {
    "record_type": "D",
    "mid": "test-mid-123",
    "location_id": "411111083",
    "aggregate_merchant_id": "",
    "amount": 1222,
    "date": "20201027",
    "time": "1501",
    "token": "token-123",
    "transaction_id": "48156a45-",
    "auth_code": "666666",
}


def test_make_settlement_key() -> None:
    settlement_key = _make_settlement_key(
        third_party_id=AUTH_TRANSACTION_1_ID,
        transaction_date=AUTH_TRANSACTION_1_DATE,
        mid=AUTH_TRANSACTION_1_MID,
        token=AUTH_TRANSACTION_1_TOKEN,
    )
    assert settlement_key == "3464063f0ca6d51ca718d5634d5956985ff920d477bc69866535e9f53749e468"


def test_find_new_transactions(db_session: db.Session) -> None:
    get_or_create_import_transaction(
        session=db_session,
        transaction_id=AUTH_TRANSACTION_1_ID + "_" + AUTH_TRANSACTION_1["time"][0:10].replace("-", ""),
        feed_type=FeedType.AUTH,
        provider_slug=PAYMENT_PROVIDER_SLUG,
        identified=True,
        match_group="5652d8f5546d4dee9c31b97ba10a6a7c",
        source="AMQP: mastercard-auth",
        data=json.dumps(AUTH_TRANSACTION_1),
    )
    provider_transactions = [AUTH_TRANSACTION_1, AUTH_TRANSACTION_2]

    new_transactions = MastercardAuth()._find_new_transactions(provider_transactions, session=db_session)

    assert new_transactions[0] == AUTH_TRANSACTION_2


def test_auth_to_transaction_fields(db_session: db.Session) -> None:
    get_or_create_merchant_identifier(
        session=db_session, identifier=AUTH_TRANSACTION_1_MID, payment_provider_slug=PAYMENT_PROVIDER_SLUG
    )
    with mock.patch("app.imports.agents.bases.base.db.session_scope", return_value=db_session):
        transaction_fields = MastercardAuth().to_transaction_fields(AUTH_TRANSACTION_1)

    assert transaction_fields == PaymentTransactionFields(
        merchant_slug="bpl-Trenette",
        payment_provider_slug="mastercard",
        transaction_date=mock.ANY,
        has_time=True,
        spend_amount=9600,
        spend_multiplier=100,
        spend_currency="GBP",
        card_token="test_card_token_1",
        settlement_key="3464063f0ca6d51ca718d5634d5956985ff920d477bc69866535e9f53749e468",
        first_six=None,
        last_four=None,
        auth_code="",
        approval_code="",
    )


def test_auth_get_transaction_id_if_third_party_id() -> None:
    transaction_id = MastercardAuth().get_transaction_id(AUTH_TRANSACTION_1)
    expected_transaction_id = AUTH_TRANSACTION_1_ID + "_" + AUTH_TRANSACTION_1["time"][0:10].replace("-", "")
    assert transaction_id == expected_transaction_id


def test_auth_get_transaction_id_no_third_party_id() -> None:
    transaction_id = MastercardAuth().get_transaction_id({"no_third_party_id": "None"})
    assert UUID(transaction_id)


def test_tgx2_settlement_parse_line() -> None:
    line = (
        "D                    token-asos-123                                                                   "
        "20200409                                                                                              "
        "                                                                                                      "
        "                                                                                                      "
        "                                           test-mid-123                                     "
        "test-mid-123test-m000000011199                                 1646666666                             "
        "                                                                                                      "
        "                                                         295d3aaa-"
    )
    assert MastercardTGX2Settlement().parse_line(line) == {
        "record_type": "D",
        "mid": "test-mid-123",
        "location_id": "test-mid-123",
        "aggregate_merchant_id": "test-m",
        "amount": "000000011199",
        "date": "20200409",
        "time": "1646",
        "token": "token-asos-123",
        "transaction_id": "295d3aaa-",
        "auth_code": "666666",
    }


def test_tgx2_settlement_yield_transaction_data() -> None:
    data = SampleTransactions().MastercardTGX2Settlement(date=pendulum.DateTime(2020, 4, 9, 16, 46, 59))
    yield_transactions_data = MastercardTGX2Settlement().yield_transactions_data(data)
    assert next(yield_transactions_data) == {
        "record_type": "D",
        "mid": "test_primary_mi",
        "location_id": "test-mid-123",
        "aggregate_merchant_id": "test-m",
        "amount": 5566,
        "date": "20200409",
        "time": "1646",
        "token": "CqN58fD9MI1s7ePn0M5F1RxRu1P",
        "transaction_id": "db0b14a3-",
        "auth_code": "472624",
    }


def test_tgx2_settlement_yield_transaction_data_incorrect_record_type() -> None:
    data = SampleTransactions().MastercardTGX2Settlement(
        record_type="A", date=pendulum.DateTime(2020, 4, 9, 16, 46, 59)
    )
    with pytest.raises(StopIteration):
        next(MastercardTGX2Settlement().yield_transactions_data(data))


@time_machine.travel(pendulum.datetime(2022, 11, 24, 9, 0, 0, 0, "Europe/London"))
def test_tgx2_settlement_to_transaction_fields(db_session: db.Session) -> None:
    get_or_create_merchant_identifier(
        session=db_session,
        identifier="test-mid-123",
        merchant_slug="bpl-asos",
        payment_provider_slug=PAYMENT_PROVIDER_SLUG,
    )
    with mock.patch("app.imports.agents.bases.base.db.session_scope", return_value=db_session):
        payment_transaction_fields = MastercardTGX2Settlement().to_transaction_fields(SETTLEMENT_TRANSACTION)

    assert payment_transaction_fields._asdict() == {
        "merchant_slug": "bpl-asos",
        "payment_provider_slug": "mastercard",
        "transaction_date": pendulum.DateTime(2020, 10, 27, 15, 1, 0, tzinfo=pendulum.timezone("Europe/London")),
        "has_time": True,
        "spend_amount": 1222,
        "spend_multiplier": 100,
        "spend_currency": "GBP",
        "card_token": "token-123",
        "settlement_key": "fa912d5e0751841ff24f028100de1234046f9c71377759eb8f4ea95cc845eae0",
        "first_six": None,
        "last_four": None,
        "auth_code": "666666",
        "approval_code": "",
        "extra_fields": None,
    }


def test_tgx2_settlement_get_transaction_id() -> None:
    transaction_id = MastercardTGX2Settlement().get_transaction_id(SETTLEMENT_TRANSACTION)
    assert transaction_id == "48156a45-_20201027"


def test_tgx2_settlement_get_transaction_id_no_id() -> None:
    transaction_id = MastercardAuth().get_transaction_id({"no_transaction_id": "None"})
    assert UUID(transaction_id)


def test_tgx2_settlement_get_transaction_date() -> None:
    assert MastercardTGX2Settlement().get_transaction_date(SETTLEMENT_TRANSACTION) == pendulum.DateTime(
        2020, 10, 27, 15, 1, 0, tzinfo=pendulum.timezone("Europe/London")
    )
