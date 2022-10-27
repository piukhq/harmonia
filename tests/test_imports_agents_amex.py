from app.imports.agents.amex import AmexAuth, AmexSettlement
from app.models import IdentifierType

auth_tx_data = {
    "transaction_id": "a46d15b6-5f9f-481f-8649-983e8d291b7e",
    "offer_id": "a46d15b6-5f9f-481f-8649-983e8d291b7e",
    "transaction_time": "2020-10-27 08:01:59",
    "transaction_amount": "12.22",
    "cm_alias": "token-123",
    "merchant_number": "test-mid-123",
    "approval_code": "666666",
}

settlement_tx_data = {
    "transactionId": "5388652c-963a-47e5-8fef-33602ec73a92",
    "offerId": "5388652c-963a-47e5-8fef-33602ec73a92",
    "transactionDate": "2020-10-27 15:01:59",
    "transactionAmount": "12.22",
    "cardToken": "token-123",
    "merchantNumber": "test-mid-123",
    "approvalCode": "666666",
    "dpan": "123456XXXXX7890",
    "partnerId": "AADP0050",
    "recordId": "0224133845625011230183160001602891525AADP00400",
    "currencyCode": "840",
}


def test_auth_get_mids():
    agent = AmexAuth()
    ids = agent.get_mids(auth_tx_data)
    assert ids == [(IdentifierType.PRIMARY, "test-mid-123")]


def test_settlement_get_mids():
    agent = AmexSettlement()
    ids = agent.get_mids(settlement_tx_data)
    assert ids == [(IdentifierType.PRIMARY, "test-mid-123")]
