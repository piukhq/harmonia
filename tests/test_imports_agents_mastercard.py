import json

from app import db, models
from app.feeds import FeedType
from app.imports.agents.mastercard import MastercardAuth, MastercardTGX2Settlement

auth_transaction_1_id = "NTI4QjdBN"
auth_transaction_1 = {
    "amount": 96,
    "currency_code": "GBP",
    "mid": "test_primary_identifier_1",
    "payment_card_token": "test_card_token_1",
    "third_party_id": auth_transaction_1_id,
    "time": "2022-10-14 13:52:24",
}
auth_transaction_2 = {
    "amount": 41,
    "currency_code": "GBP",
    "mid": "test_primary_identifier_2",
    "payment_card_token": "test_token_2",
    "third_party_id": "MkNGQjc3Q",
    "time": "2022-10-14 13:54:59",
}
settlement_transaction = {
    "record_type": "D",
    "mid": "test-mid-123",
    "amount": 1222,
    "date": "20201027",
    "time": "1501",
    "token": "token-123",
    "transaction_id": "9f2f764b-",
    "auth_code": "666666",
}


def create_transaction_record(db_session: db.Session):
    db.get_or_create(
        models.ImportTransaction,
        transaction_id=auth_transaction_1_id + "_" + auth_transaction_1["time"][0:10],
        defaults=dict(
            feed_type=FeedType.AUTH,
            provider_slug="mastercard",
            identified=True,
            match_group="5652d8f5546d4dee9c31b97ba10a6a7c",
            source="AMQP: mastercard-auth",
            data=json.dumps(auth_transaction_1),
        ),
        session=db_session,
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
    assert transaction_id == "NTI4QjdBN_20221014"


def test_get_transaction_id_settlement():
    agent = MastercardTGX2Settlement()
    transaction_id = agent.get_transaction_id(settlement_transaction)
    assert transaction_id == "9f2f764b-_20201027"
