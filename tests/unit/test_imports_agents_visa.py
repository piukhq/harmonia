import copy
import json
from unittest.mock import patch

import pendulum
import pytest

from app import db
from app.feeds import FeedType
from app.imports.agents.visa import VisaAuth, VisaRefund, VisaSettlement, get_key_value, validate_mids
from app.models import IdentifierType
from tests.unit.fixtures import Default, SampleTransactions, get_or_create_import_transaction

PRIMARY_ID = Default.primary_mids[0]
SECONDARY_ID = Default.secondary_mid
PSIMI_ID = Default.psimi
AUTH_TX1_ID = "MTY1NzkzM0EtNDI1OS00MjA2LUIxNjEtRUE1RTE2NDY3ODM0"
AUTH_TX1_AUTH_CODE = "822643"
SETTLEMENT_TX_AUTH_CODE = "6666667"
REFUND_TX_AUTH_CODE = "444444"

AUTH_TX1 = SampleTransactions().visa_auth(
    transaction_id=AUTH_TX1_ID,
    transaction_date=pendulum.DateTime(2022, 10, 14, 12, 52, 24, tzinfo=pendulum.timezone("UCT")),
    user_token="test_card_token_1",
    spend_amount=96.00,
    auth_code=AUTH_TX1_AUTH_CODE,
)
AUTH_TX1_AUTH_CODE_INDEX = AUTH_TX1.get("MessageElementsCollection").index(
    {"Key": "Transaction.AuthCode", "Value": AUTH_TX1_AUTH_CODE}
)
AUTH_TX1_PSIMI_INDEX = AUTH_TX1.get("MessageElementsCollection").index(
    {"Key": "Transaction.VisaMerchantId", "Value": PSIMI_ID}
)

AUTH_TX_2 = SampleTransactions().visa_auth(
    transaction_id="RDRGOEFEMkYtQkJFMC00MzhGLTk5MDktQjVCOEQ0M0VBM0ZD",
    transaction_date=pendulum.DateTime(2022, 10, 14, 12, 54, 59, tzinfo=pendulum.timezone("UCT")),
    mid="test_primary_mid_2",
    secondary_identifier="",
    psimi_identifier="",
    user_token="test_token_2",
    spend_amount=41.00,
    auth_code="745615",
)

SETTLEMENT_TRANSACTION = SampleTransactions().visa_settlement(
    transaction_id="32c26a8d-95be-4923-b78e-e49ac7d8812d",
    transaction_date=pendulum.DateTime(2020, 6, 2, 15, 46, 0, tzinfo=pendulum.timezone("UCT")),
    user_token="token-234",
    spend_amount=10.99,
    auth_code=SETTLEMENT_TX_AUTH_CODE,
)
SETTLEMENT_PSIMI_INDEX = SETTLEMENT_TRANSACTION.get("MessageElementsCollection").index(
    {"Key": "Transaction.VisaMerchantId", "Value": PSIMI_ID}
)
SETTLEMENT_AUTH_CODE_INDEX = SETTLEMENT_TRANSACTION.get("MessageElementsCollection").index(
    {"Key": "Transaction.AuthCode", "Value": SETTLEMENT_TX_AUTH_CODE}
)

REFUND_TRANSACTION = SampleTransactions().visa_refund(
    transaction_id="d5e121cf-f34a-47ac-be19-908fc09db1ad",
    transaction_date=pendulum.DateTime(2020, 10, 27, 15, 1, 59, tzinfo=pendulum.timezone("UCT")),
    user_token="token-123",
    spend_amount=89.45,
    auth_code=REFUND_TX_AUTH_CODE,
)
REFUND_PSIMI_INDEX = REFUND_TRANSACTION.get("MessageElementsCollection").index(
    {"Key": "ReturnTransaction.VisaMerchantId", "Value": PSIMI_ID}
)
REFUND_AUTH_CODE_INDEX = REFUND_TRANSACTION.get("MessageElementsCollection").index(
    {"Key": "ReturnTransaction.AuthCode", "Value": REFUND_TX_AUTH_CODE}
)


def test_get_key_value() -> None:
    data = copy.deepcopy(AUTH_TX1)

    assert get_key_value(data, "Transaction.MerchantCardAcceptorId") == PRIMARY_ID

    with pytest.raises(KeyError) as e:
        get_key_value(data, "not_a_valid_key")
    assert e.value.args[0] == f"Key not_a_valid_key not found in data: {data}"


@pytest.mark.parametrize(
    "input, expected",
    [
        (
            [
                (IdentifierType.PRIMARY, PRIMARY_ID),
                (IdentifierType.SECONDARY, SECONDARY_ID),
                (IdentifierType.PSIMI.value, PSIMI_ID),
            ],
            [
                (IdentifierType.PRIMARY, PRIMARY_ID),
                (IdentifierType.SECONDARY, SECONDARY_ID),
                (IdentifierType.PSIMI.value, PSIMI_ID),
            ],
        ),
        (
            [
                (IdentifierType.PRIMARY, PRIMARY_ID),
                (IdentifierType.SECONDARY, SECONDARY_ID),
                (IdentifierType.PSIMI.value, ""),
            ],
            [
                (IdentifierType.PRIMARY, PRIMARY_ID),
                (IdentifierType.SECONDARY, SECONDARY_ID),
            ],
        ),
        (
            [
                (IdentifierType.PRIMARY, PRIMARY_ID),
                (IdentifierType.SECONDARY, SECONDARY_ID),
                (IdentifierType.PSIMI.value, "0"),
            ],
            [
                (IdentifierType.PRIMARY, PRIMARY_ID),
                (IdentifierType.SECONDARY, SECONDARY_ID),
            ],
        ),
        (
            [
                (IdentifierType.PRIMARY, PRIMARY_ID),
                (IdentifierType.SECONDARY, SECONDARY_ID),
                (IdentifierType.PSIMI.value, None),
            ],
            [
                (IdentifierType.PRIMARY, PRIMARY_ID),
                (IdentifierType.SECONDARY, SECONDARY_ID),
            ],
        ),
    ],
)
def test_validate_mids(input, expected) -> None:
    ids = validate_mids(input)
    assert ids == expected


def test_find_new_transactions(db_session: db.Session) -> None:
    get_or_create_import_transaction(
        session=db_session,
        transaction_id=AUTH_TX1_ID,
        feed_type=FeedType.AUTH,
        provider_slug="visa",
        identified=True,
        match_group="e5ccfe848bd94825b921b677d3baf1b1",
        source="AMQP: visa-auth",
        data=json.dumps(AUTH_TX1),
    )
    provider_transactions = [AUTH_TX1, AUTH_TX_2]

    new_transactions = VisaAuth()._find_new_transactions(provider_transactions, session=db_session)

    assert new_transactions[0] == AUTH_TX_2


def test_settlement_get_transaction_id() -> None:
    transaction_id = VisaSettlement().get_transaction_id(SETTLEMENT_TRANSACTION)
    assert transaction_id == "32c26a8d-95be-4923-b78e-e49ac7d8812d"


def test_refund_get_transaction_id() -> None:
    transaction_id = VisaRefund().get_transaction_id(REFUND_TRANSACTION)
    assert transaction_id == "d5e121cf-f34a-47ac-be19-908fc09db1ad"


@patch("app.imports.agents.visa.VisaAuth.get_merchant_slug", return_value="merchant")
def test_auth_auth_code_field_is_missing(mock_get_merchant_slug) -> None:
    data = copy.deepcopy(AUTH_TX1)
    agent = VisaAuth()
    fields = agent.to_transaction_fields(data)
    assert fields.auth_code == AUTH_TX1_AUTH_CODE
    data["MessageElementsCollection"][AUTH_TX1_AUTH_CODE_INDEX] = {"Key": "Transaction.AuthCode", "Value": ""}
    fields = agent.to_transaction_fields(data)
    assert fields.auth_code == ""
    data["MessageElementsCollection"].pop(AUTH_TX1_AUTH_CODE_INDEX)
    fields = agent.to_transaction_fields(data)
    assert fields.auth_code == ""


@patch("app.imports.agents.visa.VisaRefund.get_merchant_slug", return_value="merchant")
def test_refund_auth_code_field_is_missing(mock_get_merchant_slug) -> None:
    data = copy.deepcopy(REFUND_TRANSACTION)
    agent = VisaRefund()
    fields = agent.to_transaction_fields(data)
    assert fields.auth_code == REFUND_TX_AUTH_CODE
    data["MessageElementsCollection"][REFUND_AUTH_CODE_INDEX] = {"Key": "ReturnTransaction.AuthCode", "Value": ""}
    fields = agent.to_transaction_fields(data)
    assert fields.auth_code == ""
    data["MessageElementsCollection"].pop(REFUND_AUTH_CODE_INDEX)
    fields = agent.to_transaction_fields(data)
    assert fields.auth_code == ""


@patch("app.imports.agents.visa.VisaSettlement.get_merchant_slug", return_value="merchant")
def test_settlement_auth_code_field_is_missing(mock_get_merchant_slug) -> None:
    data = copy.deepcopy(SETTLEMENT_TRANSACTION)
    agent = VisaSettlement()
    fields = agent.to_transaction_fields(data)
    assert fields.auth_code == SETTLEMENT_TX_AUTH_CODE
    data["MessageElementsCollection"][SETTLEMENT_AUTH_CODE_INDEX] = {"Key": "Transaction.AuthCode", "Value": ""}
    fields = agent.to_transaction_fields(data)
    assert fields.auth_code == ""
    data["MessageElementsCollection"].pop(SETTLEMENT_AUTH_CODE_INDEX)
    fields = agent.to_transaction_fields(data)
    assert fields.auth_code == ""
