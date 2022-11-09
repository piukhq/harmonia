from app.imports.agents.amex import AmexAuth, AmexSettlement
from app.models import IdentifierType
from tests.fixtures import Default, SampleTransactions


def test_auth_get_mids():
    agent = AmexAuth()
    ids = agent.get_mids(SampleTransactions.amex_auth)
    assert ids == [(IdentifierType.PRIMARY, Default.primary_identifier)]


def test_settlement_get_mids():
    agent = AmexSettlement()
    ids = agent.get_mids(SampleTransactions.amex_settlement)
    assert ids == [(IdentifierType.PRIMARY, Default.primary_identifier)]
