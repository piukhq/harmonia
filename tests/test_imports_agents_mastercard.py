from app import db
from app.imports.agents.mastercard import MastercardAuth


def test_find_new_transactions(db_session: db.Session):
    provider_transactions = [
        {
            "third_party_id": "3026d4b0-",
            "time": "2020-10-27 15:01:59",
            "amount": "12.22",
            "currency_code": "GBP",
            "payment_card_token": "token-123",
            "mid": "test-mid-123",
        }
    ]

    agent = MastercardAuth()
    agent._find_new_transactions(provider_transactions, db_session)