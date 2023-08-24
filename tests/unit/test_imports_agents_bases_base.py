import logging
from collections import defaultdict
from unittest import mock

import pendulum
import pytest
from redis.lock import Lock

from app import db, models
from app.feeds import FeedType
from app.imports.agents.bases.base import (
    BaseAgent,
    IdentifyArgs,
    PaymentTransactionFields,
    SchemeTransactionFields,
    find_identifiers,
)
from app.imports.agents.visa import VisaAuth
from app.imports.exceptions import MissingMID
from app.models import IdentifierType, TransactionStatus
from tests.fixtures import Default, SampleTransactions, get_or_create_merchant_identifier

PAYMENT_PROVIDER_SLUG = "visa"
MATCH_GROUP = "da34aa2a4abf4cc190c3519f7c6e2f88"
SOURCE = "AMQP: visa-auth"
TRANSACTION_DATE = pendulum.DateTime(2022, 12, 20, 9, 0, 0, tzinfo=pendulum.timezone("UCT"))
CARD_TOKEN = "CqN58fD9MI1s7ePn0M5F1RxRu1P"

MIDS_DATA = [
    *[(IdentifierType.PRIMARY, mid) for mid in Default.primary_mids],
    (IdentifierType.SECONDARY, Default.secondary_mid),
    (IdentifierType.PSIMI, Default.psimi),
]

VISA_TRANSACTION = SampleTransactions().visa_auth(transaction_date=TRANSACTION_DATE)

IMPORT_TRANSACTION_INSERT = {
    "transaction_id": Default.transaction_id,
    "feed_type": FeedType.AUTH,
    "provider_slug": PAYMENT_PROVIDER_SLUG,
    "identified": True,
    "match_group": MATCH_GROUP,
    "data": VISA_TRANSACTION,
    "source": SOURCE,
}
TRANSACTION_INSERT = {
    "feed_type": FeedType.AUTH,
    "status": TransactionStatus.IMPORTED,
    "merchant_identifier_ids": [1],
    "transaction_id": Default.transaction_id,
    "match_group": MATCH_GROUP,
    "merchant_slug": Default.merchant_slug,
    "payment_provider_slug": PAYMENT_PROVIDER_SLUG,
    "mids": Default.primary_mids,
    "transaction_date": TRANSACTION_DATE.replace(microsecond=0),
    "has_time": True,
    "spend_amount": Default.spend_amount,
    "spend_multiplier": Default.spend_multiplier,
    "spend_currency": "GBP",
    "card_token": Default.user_token,
    "settlement_key": "33ffec57b443bec64d34d84f20590a6c88f4d0f4fad548bb2a5fb545d817128e",
    "first_six": None,
    "last_four": None,
    "auth_code": Default.auth_code,
    "approval_code": "",
    "extra_fields": None,
}
IDENTIFY = IdentifyArgs(
    transaction_id=Default.transaction_id,
    merchant_identifier_ids=[1],
    card_token=Default.user_token,
)
PAYMENT_TRANSACTION_FIELDS = PaymentTransactionFields(
    merchant_slug=Default.merchant_slug,
    payment_provider_slug=PAYMENT_PROVIDER_SLUG,
    transaction_date=TRANSACTION_DATE,
    has_time=True,
    spend_amount=5566,
    spend_multiplier=100,
    spend_currency="GBP",
    card_token=CARD_TOKEN,
    settlement_key="33ffec57b443bec64d34d84f20590a6c88f4d0f4fad548bb2a5fb545d817128e",
    first_six=None,
    last_four=None,
    auth_code="472624",
    approval_code="",
)
SCHEME_TRANSACTION_FIELDS = SchemeTransactionFields(
    merchant_slug=Default.merchant_slug,
    payment_provider_slug=PAYMENT_PROVIDER_SLUG,
    transaction_date=TRANSACTION_DATE,
    has_time=True,
    spend_amount=6000,
    spend_multiplier=100,
    spend_currency="GBP",
)


class MockBaseAgent(BaseAgent):
    provider_slug = PAYMENT_PROVIDER_SLUG


@pytest.fixture
def mid_primary(db_session: db.Session) -> int:
    mid = get_or_create_merchant_identifier(
        session=db_session, payment_provider_slug=PAYMENT_PROVIDER_SLUG, location_id="12345678"
    )

    return mid.id


@pytest.fixture
def mid_secondary(db_session: db.Session) -> int:
    mid = get_or_create_merchant_identifier(
        session=db_session,
        identifier=Default.secondary_mid,
        identifier_type=IdentifierType.SECONDARY,
        payment_provider_slug=PAYMENT_PROVIDER_SLUG,
    )
    return mid.id


# TODO: this isn't used, but should be to test this edge case
@pytest.fixture
def mid_primary_duplicate(db_session: db.Session) -> int:
    mid = get_or_create_merchant_identifier(
        session=db_session,
        identifier_type=IdentifierType.PSIMI,
        payment_provider_slug=PAYMENT_PROVIDER_SLUG,
    )
    return mid.id


def test_identify_primary_mids_visa(mid_primary: int, db_session: db.Session) -> None:
    agent = VisaAuth()
    identifer = agent._identify_mids(MIDS_DATA, db_session)

    assert identifer == [mid_primary]


def test_identify_secondary_mids_visa(mid_secondary: int, db_session: db.Session) -> None:
    agent = VisaAuth()
    identifer = agent._identify_mids(MIDS_DATA, db_session)

    assert identifer == [mid_secondary]


def test_identify_mixed_identifiers_visa(mid_secondary: int, mid_primary: int, db_session: db.Session) -> None:
    agent = VisaAuth()
    identifer = agent._identify_mids(MIDS_DATA, db_session)

    assert identifer == [mid_primary]


def test_identify_mixed_identifiers(mid_secondary: int, mid_primary: int, db_session: db.Session) -> None:
    mids = MIDS_DATA
    provider_slug = PAYMENT_PROVIDER_SLUG
    identifer_dict = find_identifiers(*mids, provider_slug=provider_slug, session=db_session)

    assert identifer_dict == {IdentifierType.SECONDARY: mid_secondary, IdentifierType.PRIMARY: mid_primary}


def test_identify_mids_no_matching_identifiers_visa(db_session: db.Session) -> None:
    agent = VisaAuth()
    with pytest.raises(MissingMID) as e:
        agent._identify_mids(MIDS_DATA, db_session)

    assert e.typename == "MissingMID"


def test_get_merchant_slug_primary_mid_visa(mid_primary: int, db_session: db.Session) -> None:
    with mock.patch("app.db.session_scope", return_value=db_session):
        agent = VisaAuth()
        slug = agent.get_merchant_slug(VISA_TRANSACTION)
        assert slug == Default.merchant_slug


def test_get_merchant_slug_secondary_mid_visa(mid_secondary: int, db_session: db.Session) -> None:
    with mock.patch("app.db.session_scope", return_value=db_session):
        agent = VisaAuth()
        slug = agent.get_merchant_slug(VISA_TRANSACTION)
        assert slug == Default.merchant_slug


def test_provider_slug_not_implemented() -> None:
    with pytest.raises(NotImplementedError) as e:
        BaseAgent()
    assert e.value.args[0] == "BaseAgent is missing a required property: provider_slug"


def test_feed_type_not_implemented() -> None:
    with pytest.raises(NotImplementedError) as e:
        MockBaseAgent().feed_type
    assert e.value.args[0] == "MockBaseAgent is missing a required property: feed_type"


def test_feed_type_is_payment_true() -> None:
    class MockBaseAgentFeedtype(BaseAgent):
        provider_slug = "slow_slug"
        feed_type = FeedType.AUTH

    assert MockBaseAgentFeedtype().feed_type_is_payment is True


def test_feed_type_is_payment_false() -> None:
    class MockBaseAgentFeedtype(BaseAgent):
        provider_slug = "slow_slug"
        feed_type = FeedType.MERCHANT

    assert MockBaseAgentFeedtype().feed_type_is_payment is False


def test_run_not_implemented() -> None:
    with pytest.raises(NotImplementedError) as e:
        MockBaseAgent().run()
    assert (
        e.value.args[0]
        == "Override the run method in your agent to act as the main entry point into the import process."
    )


def test_to_transaction_fields_not_implemented() -> None:
    with pytest.raises(NotImplementedError) as e:
        MockBaseAgent().to_transaction_fields(data={})
    assert e.value.args[0] == "Override to_transaction_fields in your agent."


def test_get_transaction_id_not_implemented() -> None:
    with pytest.raises(NotImplementedError) as e:
        MockBaseAgent().get_transaction_id(data={})
    assert e.value.args[0] == "Override get_transaction_id in your agent."


def test_location_id_mid_map(mid_primary: int, db_session: db.Session) -> None:
    class MockMerchantBaseAgent(BaseAgent):
        provider_slug = Default.merchant_slug

    with mock.patch("app.imports.agents.bases.base.db.session_scope", return_value=db_session):
        location_id_mid_map = MockMerchantBaseAgent().location_id_mid_map

    assert location_id_mid_map == defaultdict(list, {"12345678": ["test_primary_mid"]})


def test_get_primary_mids_not_implemented() -> None:
    with pytest.raises(NotImplementedError) as e:
        MockBaseAgent().get_primary_mids(data={})
    assert e.value.args[0] == "Override get_primary_mids in your agent."


@mock.patch.object(BaseAgent, "_build_inserts")
@mock.patch.object(BaseAgent, "get_primary_mids", return_value=Default.primary_mids)
@mock.patch.object(BaseAgent, "feed_type", new_callable=mock.PropertyMock, return_value=FeedType.AUTH)
@mock.patch.object(BaseAgent, "get_transaction_id", return_value=Default.transaction_id)
def test_import_transactions(
    mock_get_transaction_id,
    mock_feed_type,
    mock_get_primary_mids,
    mock_build_inserts,
    mid_primary: int,
    db_session: db.Session,
    caplog,
) -> None:
    body = VISA_TRANSACTION
    agent = MockBaseAgent()
    caplog.set_level(logging.DEBUG)
    agent.log.propagate = True
    mock_build_inserts.return_value = IMPORT_TRANSACTION_INSERT, TRANSACTION_INSERT, IDENTIFY

    # Check that there are no existing import transactions
    assert db_session.query(models.ImportTransaction).count() == 0
    assert db_session.query(models.Transaction).count() == 0

    # Check that one import transaction is added, with the expected transaction_id
    result = list(agent._import_transactions([body], source=SOURCE, session=db_session))
    assert result == [None]
    assert db_session.query(models.ImportTransaction.transaction_id).one()[0] == Default.transaction_id
    assert db_session.query(models.Transaction.transaction_id).one()[0] == Default.transaction_id

    # Check that there are no new import transactions once one has been added
    result = list(agent._import_transactions([body], source=SOURCE, session=db_session))
    assert result == []
    assert caplog.messages[0] == "Found 1 new transactions in import set of 1 total transactions."
    assert caplog.messages[2] == "Found 0 new transactions in import set of 1 total transactions."
    assert caplog.messages[3] == f'No new transactions found in source "{SOURCE}", exiting early.'


@mock.patch.object(BaseAgent, "get_primary_mids", return_value=Default.primary_mids)
@mock.patch.object(BaseAgent, "feed_type", new_callable=mock.PropertyMock, return_value=FeedType.AUTH)
@mock.patch.object(BaseAgent, "get_transaction_id", return_value=Default.transaction_id)
def test_import_transactions_lock_acquire_false(
    mock_get_transaction_id, mock_feed_type, mock_get_primary_mids, db_session: db.Session, caplog
) -> None:
    agent = MockBaseAgent()
    caplog.set_level(logging.DEBUG)
    agent.log.propagate = True

    with mock.patch.object(Lock, "acquire", return_value=False):
        list(agent._import_transactions([VISA_TRANSACTION], source=SOURCE, session=db_session))

    assert caplog.messages == [
        "Found 1 new transactions in import set of 1 total transactions.",
        f"Transaction txmatch:import-lock:{PAYMENT_PROVIDER_SLUG}:{Default.transaction_id} is already locked. "
        "Skipping.",
    ]


@mock.patch("app.imports.agents.bases.base.tasks.import_queue.enqueue")
@mock.patch("app.imports.agents.bases.base.tasks.identify_user_queue.enqueue")
@mock.patch.object(BaseAgent, "_update_metrics")
@mock.patch.object(BaseAgent, "feed_type", new_callable=mock.PropertyMock, return_value=FeedType.AUTH)
def test_persist_and_enqueue_payment_feed(
    mock_feed_type,
    mock_update_metrics,
    mock_enqueue_identify_user_queue,
    mock_enqueue_import_queue,
    db_session: db.Session,
) -> None:
    agent = MockBaseAgent()
    agent._persist_and_enqueue([IMPORT_TRANSACTION_INSERT], [TRANSACTION_INSERT], [IDENTIFY], MATCH_GROUP)

    assert mock_enqueue_identify_user_queue.call_args.args[0].__name__ == "identify_user"
    assert mock_enqueue_identify_user_queue.call_args.kwargs == {
        "feed_type": FeedType.AUTH,
        "transaction_id": Default.transaction_id,
        "merchant_identifier_ids": [1],
        "card_token": CARD_TOKEN,
        "match_group": MATCH_GROUP,
    }
    assert mock_enqueue_import_queue.called is False


@mock.patch("app.imports.agents.bases.base.tasks.import_queue.enqueue")
@mock.patch("app.imports.agents.bases.base.tasks.identify_user_queue.enqueue")
@mock.patch.object(BaseAgent, "_update_metrics")
@mock.patch.object(BaseAgent, "feed_type", new_callable=mock.PropertyMock, return_value=FeedType.MERCHANT)
def test_persist_and_enqueue_merchant_feed(
    mock_feed_type,
    mock_update_metrics,
    mock_enqueue_identify_user_queue,
    mock_enqueue_import_queue,
    db_session: db.Session,
) -> None:
    agent = MockBaseAgent()
    agent._persist_and_enqueue([IMPORT_TRANSACTION_INSERT], [TRANSACTION_INSERT], [IDENTIFY], MATCH_GROUP)

    assert mock_enqueue_identify_user_queue.called is False
    assert mock_enqueue_import_queue.call_args.args[0].__name__ == "import_transactions"
    assert mock_enqueue_import_queue.call_args.args[1] == MATCH_GROUP


@mock.patch.object(BaseAgent, "to_transaction_fields", return_value=PAYMENT_TRANSACTION_FIELDS)
@mock.patch.object(BaseAgent, "_identify_mids", return_value=[1])
@mock.patch.object(BaseAgent, "feed_type", new_callable=mock.PropertyMock, return_value=FeedType.AUTH)
@mock.patch.object(BaseAgent, "get_primary_mids", return_value=Default.primary_mids)
@mock.patch.object(BaseAgent, "get_transaction_id", return_value=Default.transaction_id)
@mock.patch("app.imports.agents.bases.base.get_merchant_slug", return_value=Default.merchant_slug)
def test_build_inserts(
    mock_get_merchant_slug,
    mock_get_transaction_id,
    mock_get_primary_mids,
    mock_feed_type,
    mock_identify_mids,
    mock_to_transaction_fields,
    mid_primary: int,
    mid_secondary: int,
    db_session: db.Session,
) -> None:
    agent = MockBaseAgent()
    import_transaction_insert, transaction_insert, identify = agent._build_inserts(
        tx_data=VISA_TRANSACTION, match_group=MATCH_GROUP, source=SOURCE, session=db_session
    )

    assert import_transaction_insert == IMPORT_TRANSACTION_INSERT
    assert transaction_insert == TRANSACTION_INSERT
    assert identify == IDENTIFY


@mock.patch.object(BaseAgent, "to_transaction_fields", return_value=SCHEME_TRANSACTION_FIELDS)
@mock.patch.object(BaseAgent, "_identify_mids", return_value=[1])
@mock.patch.object(BaseAgent, "feed_type", new_callable=mock.PropertyMock, return_value=FeedType.AUTH)
@mock.patch.object(BaseAgent, "get_primary_mids", return_value=Default.primary_mids)
@mock.patch.object(BaseAgent, "get_transaction_id", return_value=Default.transaction_id)
@mock.patch("app.imports.agents.bases.base.get_merchant_slug", return_value=Default.merchant_slug)
def test_build_inserts_import_error(
    mock_get_merchant_slug,
    mock_get_transaction_id,
    mock_get_primary_mids,
    mock_feed_type,
    mock_identify_mids,
    mock_to_transaction_fields,
    mid_primary: int,
    mid_secondary: int,
    db_session: db.Session,
) -> None:
    agent = MockBaseAgent()
    with pytest.raises(BaseAgent.ImportError) as e:
        agent._build_inserts(tx_data=VISA_TRANSACTION, match_group=MATCH_GROUP, source=SOURCE, session=db_session)

    assert (
        e.value.args[0] == "visa agent is configured with a feed type of FeedType.AUTH,  but provided "
        "SchemeTransactionFields instead of PaymentTransactionFields"
    )
