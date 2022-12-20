from decimal import Decimal

import pendulum
import pytest

from app.imports.agents.iceland import Iceland
from app.models import IdentifierType
from app.service.hermes import PaymentProviderSlug


TRANSACTION_DATA = {
    "TransactionCardFirst6": "123456",
    "TransactionCardLast4": "7890",
    "TransactionCardExpiry": "01/80",
    "TransactionCardSchemeId": 1,
    "TransactionCardScheme": "Amex",
    "TransactionStore_Id": "test-mid-123",
    "TransactionTimestamp": pendulum.DateTime(2020, 10, 27, 15, 1, 59, tzinfo=pendulum.timezone("Europe/London")),
    "TransactionAmountValue": 1222,
    "TransactionAmountUnit": "GBP",
    "TransactionCashbackValue": Decimal("0.00"),
    "TransactionCashbackUnit": "GBP",
    "TransactionId": "1a4ac684-f4cb-4a12-be40-c7d54824543e",
    "TransactionAuthCode": "666666",
}


def test_yield_transactions_data() -> None:
    transaction = (
        b"TransactionCardFirst6,TransactionCardLast4,TransactionCardExpiry,TransactionCardSchemeId,"
        b"TransactionCardScheme,TransactionStore_Id,TransactionTimestamp,TransactionAmountValue,"
        b"TransactionAmountUnit,TransactionCashbackValue,TransactionCashbackUnit,TransactionId,"
        b"TransactionAuthCode\r\n123456,7890,01/80,1,Amex,test-mid-123,2020-10-27 15:01:59,12.22,GBP,"
        b".00,GBP,1a4ac684-f4cb-4a12-be40-c7d54824543e,666666\r\n"
    )
    generator = Iceland().yield_transactions_data(transaction)
    assert next(generator) == TRANSACTION_DATA


def test_yield_transactions_data_auth_code_is_decline() -> None:
    transaction = (
        b"TransactionCardFirst6,TransactionCardLast4,TransactionCardExpiry,TransactionCardSchemeId,"
        b"TransactionCardScheme,TransactionStore_Id,TransactionTimestamp,TransactionAmountValue,"
        b"TransactionAmountUnit,TransactionCashbackValue,TransactionCashbackUnit,TransactionId,"
        b"TransactionAuthCode\r\n123456,7890,01/80,1,Amex,test-mid-123,2020-10-27 15:01:59,12.22,GBP,"
        b".00,GBP,1a4ac684-f4cb-4a12-be40-c7d54824543e,decline\r\n"
    )
    generator = Iceland().yield_transactions_data(transaction)

    with pytest.raises(StopIteration):
        next(generator)


def test_yield_transactions_data_no_card_scheme() -> None:
    transaction = (
        b"TransactionCardFirst6,TransactionCardLast4,TransactionCardExpiry,TransactionCardSchemeId,"
        b"TransactionCardScheme,TransactionStore_Id,TransactionTimestamp,TransactionAmountValue,"
        b"TransactionAmountUnit,TransactionCashbackValue,TransactionCashbackUnit,TransactionId,"
        b"TransactionAuthCode\r\n123456,7890,01/80,1,Another Provider,test-mid-123,2020-10-27 15:01:59,"
        b"12.22,GBP,.00,GBP,1a4ac684-f4cb-4a12-be40-c7d54824543e,666666\r\n"
    )
    generator = Iceland().yield_transactions_data(transaction)

    with pytest.raises(StopIteration):
        next(generator)


def test_to_transaction_fields() -> None:
    scheme_transaction_fields = Iceland().to_transaction_fields(TRANSACTION_DATA)
    assert scheme_transaction_fields._asdict() == {
        "merchant_slug": "iceland-bonus-card",
        "payment_provider_slug": PaymentProviderSlug.AMEX,
        "transaction_date": pendulum.DateTime(2020, 10, 27, 15, 1, 59, tzinfo=pendulum.timezone("Europe/London")),
        "has_time": True,
        "spend_amount": 1222,
        "spend_multiplier": 100,
        "spend_currency": "GBP",
        "first_six": "123456",
        "last_four": "7890",
        "auth_code": "666666",
    }


def test_get_transaction_id() -> None:
    transaction_id = Iceland().get_transaction_id(TRANSACTION_DATA)
    assert transaction_id == "1a4ac684-f4cb-4a12-be40-c7d54824543e"


def test_get_mids() -> None:
    mids = Iceland().get_mids(TRANSACTION_DATA)
    assert mids == [(IdentifierType.PRIMARY, "test-mid-123")]


def test_get_transaction_date() -> None:
    transaction_date = Iceland().get_transaction_date(TRANSACTION_DATA)
    assert transaction_date == pendulum.DateTime(2020, 10, 27, 15, 1, 59, tzinfo=pendulum.timezone("Europe/London"))
