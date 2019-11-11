import os
import csv
import glob
import pytest

from app import models
from s import s_settings
from app.db import session
from decimal import Decimal


FLAG = False if s_settings.ICELAND_END_TO_END_TEST or os.path.isfile("/tmp/end_to_end_active") else True


def get_latest_input_file():
    latest_folder = max(glob.glob(f"../harmonia/files/archives/*"), key=os.path.getctime) + "/*"
    return max(glob.glob(latest_folder), key=os.path.getctime)


def read_input_file():
    json_input_file = get_latest_input_file()
    with open(json_input_file, "r") as csv_data_file:
        csv_data = csv.DictReader(csv_data_file)
        return [x for x in csv_data]


@pytest.fixture(scope="session", autouse=True)
def run_end_to_end():
    os.system("pipenv run s/quick_work_iceland")
    os.system("pipenv run rm /tmp/end_to_end_active")
    pytest.mock_file = read_input_file()


@pytest.mark.skipif(FLAG, reason="test run occasionally")
def test_payment_transaction():
    expected = pytest.mock_file
    payment_transaction_one = session.query(models.PaymentTransaction).get(1)
    assert payment_transaction_one.spend_amount == int(Decimal(expected[0]["TransactionAmountValue"]) * 100)
    assert payment_transaction_one.spend_multiplier == 100
    assert payment_transaction_one.spend_currency == expected[0]["TransactionCashbackUnit"]
    assert payment_transaction_one.status.name == "MATCHED"


@pytest.mark.skipif(FLAG, reason="test run occasionally")
def test_scheme_transaction():
    expected = pytest.mock_file
    scheme_transaction = session.query(models.SchemeTransaction).get(1)
    assert scheme_transaction.transaction_id == expected[0]["TransactionId"]
    assert scheme_transaction.spend_amount == int(Decimal(expected[0]["TransactionAmountValue"]) * 100)
    assert scheme_transaction.spend_multiplier == 100
    assert scheme_transaction.spend_currency == expected[0]["TransactionCashbackUnit"]
    assert scheme_transaction.status.name == "MATCHED"


@pytest.mark.skipif(FLAG, reason="test run occasionally")
def test_import_transactions():
    expected = pytest.mock_file
    import_transaction = session.query(models.ImportTransaction).all()
    assert import_transaction[0].provider_slug == "bink-payment"
    assert import_transaction[0].data["spend"] == int(Decimal(expected[0]["TransactionAmountValue"]) * 100)
    assert import_transaction[2].transaction_id == expected[0]["TransactionId"]
    assert import_transaction[2].provider_slug == "iceland-bonus-card"
    assert import_transaction[2].data["TransactionAmountValue"] == int(
        Decimal(expected[0]["TransactionAmountValue"]) * 100
    )


@pytest.mark.skipif(FLAG, reason="test run occasionally")
def test_matched_transaction():
    expected = pytest.mock_file
    matched_transaction = session.query(models.MatchedTransaction).get(1)
    assert matched_transaction.transaction_id == expected[0]["TransactionId"]
    assert matched_transaction.spend_amount == int(Decimal(expected[0]["TransactionAmountValue"]) * 100)
    assert matched_transaction.status.name == "EXPORTED"


@pytest.mark.skipif(FLAG, reason="test run occasionally")
def test_export_transaction():
    expected = pytest.mock_file
    export_transaction = session.query(models.ExportTransaction).get(1)
    pending_export = session.query(models.PendingExport).all()
    assert export_transaction.transaction_id == expected[0]["TransactionId"]
    assert export_transaction.provider_slug == "iceland-bonus-card"
    assert len(pending_export) == 0
