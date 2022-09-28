from app.imports.agents.mastercard import MastercardAuth, MastercardTGX2Settlement
from app.models import IdentifierType

auth_tx_data = {
    "third_party_id": "48156a45-",
    "time": "2020-10-27 15:01:59",
    "amount": "12.22",
    "currency_code": "GBP",
    "payment_card_token": "token-123",
    "mid": "test-mid-123",
}


settlement_tx_data = {
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


settlement_tx_data_empty_psimi = {
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


def test_auth_get_mids():
    agent = MastercardAuth()
    ids = agent.get_mids(auth_tx_data)
    assert ids == [(IdentifierType.PRIMARY, "test-mid-123")]


def test_tgx2_settlement_get_mids():
    agent = MastercardTGX2Settlement()
    ids = agent.get_mids(settlement_tx_data)
    assert ids == [
        (IdentifierType.PRIMARY, "test-mid-123"),
        (IdentifierType.SECONDARY, "411111083"),
        (IdentifierType.PSIMI, "664567"),
    ]


def test_tgx2_settlement_get_mids_empty_psimi():
    agent = MastercardTGX2Settlement()
    ids = agent.get_mids(settlement_tx_data_empty_psimi)
    assert ids == [
        (IdentifierType.PRIMARY, "test-mid-123"),
        (IdentifierType.SECONDARY, "411111083"),
    ]
