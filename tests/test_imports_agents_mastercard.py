import json

from app import db, models
from app.feeds import FeedType
from app.imports.agents.mastercard import MastercardAuth, MastercardTGX2Settlement
from app.models import IdentifierType
from tests.fixtures import SampleTransactions, create_import_transaction

auth_transaction_1_id = "NTI4QjdBN"
auth_transaction_1 = SampleTransactions().mastercard_auth(
    amount=96,
    mid="test_primary_identifier_1",
    payment_card_token="test_card_token_1",
    third_party_id=auth_transaction_1_id,
    time="2022-10-14 13:52:24",
)
auth_transaction_2 = SampleTransactions().mastercard_auth(
    amount=41,
    mid="test_primary_identifier_2",
    payment_card_token="test_token_2",
    time="2022-10-14 13:54:59",
)
settlement_transaction = {
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
settlement_transaction_empty_psimi = {
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
mastercard_settlement_file = SampleTransactions().mastercard_settlement_file()


def create_transaction_record(db_session: db.Session):
    create_import_transaction(
        session=db_session,
        transaction_id=auth_transaction_1_id + "_" + auth_transaction_1["time"][0:10].replace("-", ""),
        feed_type=FeedType.AUTH,
        provider_slug="mastercard",
        identified=True,
        match_group="5652d8f5546d4dee9c31b97ba10a6a7c",
        source="AMQP: mastercard-auth",
        data=json.dumps(auth_transaction_1),
    )


def test_find_new_transactions(db_session: db.Session):
    create_transaction_record(db_session)
    provider_transactions = [auth_transaction_1, auth_transaction_2]

    agent = MastercardAuth()
    new_transactions = agent._find_new_transactions(provider_transactions, session=db_session)

    assert new_transactions[0] == auth_transaction_2


def test_get_transaction_id_auth():
    agent = MastercardAuth()
    transaction_id = agent.get_transaction_id(auth_transaction_1)
    expected_transaction_id = auth_transaction_1_id + "_" + auth_transaction_1["time"][0:10].replace("-", "")
    assert transaction_id == expected_transaction_id


def test_get_transaction_id_settlement():
    agent = MastercardTGX2Settlement()
    transaction_id = agent.get_transaction_id(settlement_transaction)
    assert transaction_id == "48156a45-_20201027"


def test_auth_get_mids():
    agent = MastercardAuth()
    ids = agent.get_mids(auth_transaction_1)
    assert ids == [(IdentifierType.PRIMARY, "test_primary_identifier_1")]


def test_tgx2_settlement_get_mids():
    agent = MastercardTGX2Settlement()
    ids = agent.get_mids(settlement_transaction)
    assert ids == [
        (IdentifierType.PRIMARY, "test-mid-123"),
        (IdentifierType.SECONDARY, "411111083"),
        (IdentifierType.PSIMI, "664567"),
    ]


def test_tgx2_settlement_get_mids_empty_psimi():
    agent = MastercardTGX2Settlement()
    ids = agent.get_mids(settlement_transaction_empty_psimi)
    assert ids == [
        (IdentifierType.PRIMARY, "test-mid-123"),
        (IdentifierType.SECONDARY, "411111083"),
    ]
