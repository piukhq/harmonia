import json

from app import db
from app.feeds import FeedType
from app.imports.agents.mastercard import MastercardAuth, MastercardTGX2Settlement
from app.models import IdentifierType
from tests.fixtures import SampleTransactions, get_or_create_import_transaction

AUTH_TRANSACTION_1_ID = "NTI4QjdBN"
AUTH_TRANSACTION_1 = SampleTransactions().mastercard_auth(
    amount=96,
    mid="test_primary_identifier_1",
    payment_card_token="test_card_token_1",
    third_party_id=AUTH_TRANSACTION_1_ID,
    time="2022-10-14 13:52:24",
)
AUTH_TRANSACTION_2 = SampleTransactions().mastercard_auth(
    amount=41,
    mid="test_primary_identifier_2",
    payment_card_token="test_token_2",
    time="2022-10-14 13:54:59",
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


def test_find_new_transactions(db_session: db.Session):
    get_or_create_import_transaction(
        session=db_session,
        transaction_id=AUTH_TRANSACTION_1_ID + "_" + AUTH_TRANSACTION_1["time"][0:10].replace("-", ""),
        feed_type=FeedType.AUTH,
        provider_slug="mastercard",
        identified=True,
        match_group="5652d8f5546d4dee9c31b97ba10a6a7c",
        source="AMQP: mastercard-auth",
        data=json.dumps(AUTH_TRANSACTION_1),
    )
    provider_transactions = [AUTH_TRANSACTION_1, AUTH_TRANSACTION_2]

    agent = MastercardAuth()
    new_transactions = agent._find_new_transactions(provider_transactions, session=db_session)

    assert new_transactions[0] == AUTH_TRANSACTION_2


def test_get_transaction_id_auth():
    agent = MastercardAuth()
    transaction_id = agent.get_transaction_id(AUTH_TRANSACTION_1)
    expected_transaction_id = AUTH_TRANSACTION_1_ID + "_" + AUTH_TRANSACTION_1["time"][0:10].replace("-", "")
    assert transaction_id == expected_transaction_id


def test_get_transaction_id_settlement():
    agent = MastercardTGX2Settlement()
    transaction_id = agent.get_transaction_id(SETTLEMENT_TRANSACTION)
    assert transaction_id == "48156a45-_20201027"


def test_auth_get_mids():
    agent = MastercardAuth()
    ids = agent.get_mids(AUTH_TRANSACTION_1)
    assert ids == [(IdentifierType.PRIMARY, "test_primary_identifier_1")]


def test_tgx2_settlement_get_mids():
    agent = MastercardTGX2Settlement()
    ids = agent.get_mids(SETTLEMENT_TRANSACTION)
    assert ids == [
        (IdentifierType.PRIMARY, "test-mid-123"),
        (IdentifierType.SECONDARY, "411111083"),
        (IdentifierType.PSIMI, "664567"),
    ]


def test_tgx2_settlement_get_mids_empty_psimi():
    agent = MastercardTGX2Settlement()
    ids = agent.get_mids(SETTLEMENT_TRANSACTION_EMPTY_PSIMI)
    assert ids == [
        (IdentifierType.PRIMARY, "test-mid-123"),
        (IdentifierType.SECONDARY, "411111083"),
    ]
