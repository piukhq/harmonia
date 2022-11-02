import pendulum
import responses

from app import db, models
from app.exports.agents import AgentExportData, AgentExportDataOutput
from app.exports.agents.squaremeal import SquareMeal
from app.exports.models import ExportTransaction
from app.feeds import FeedType


def create_transaction_record(db_session: db.Session):
    transaction = db.get_or_create(
        models.Transaction,
        transaction_id="1234567",
        defaults=dict(
            payment_provider_slug="amex",
            feed_type=FeedType.AUTH,
            status="IMPORTED",
            merchant_identifier_ids=[1],
            merchant_slug="squaremeal",
            settlement_key="123456",
            match_group="98765",
            transaction_date=pendulum.now(),
            has_time=True,
            spend_amount=5566,
            spend_multiplier=1,
            spend_currency="GBR",
            card_token="9876543",
            first_six="666666",
            last_four="4444",
            auth_code="666655",
            primary_identifier="test-mid-primary",
        ),
        session=db_session,
    )
    return transaction


def create_export_transaction(transaction_id, merchant_identifier, settlement_key) -> models.ExportTransaction:
    exp_txn = models.ExportTransaction(
        transaction_id=transaction_id,
        loyalty_id=merchant_identifier,
        mid="1234567",
        provider_slug="squaremeal",
        transaction_date=pendulum.DateTime(2022, 11, 1, 17, 14, 8, 838138, tzinfo=pendulum.timezone("Europe/London")),
        spend_amount=5566,
        spend_currency="GBP",
        payment_card_account_id=1,
        feed_type=FeedType.AUTH,
        settlement_key=settlement_key,
        user_id=1,
        scheme_account_id=1,
        credentials="something",
        primary_identifier="test-mid-primary",
    )
    return exp_txn


@responses.activate
def test_get_settlement_key_without_settlement_key(db_session: db.Session) -> None:
    create_transaction_record(db_session)
    exp_txn = create_export_transaction("1234567", 10, None)
    expected_settlement_key = "123456"
    squaremeal = SquareMeal()
    settlement_key = squaremeal.get_settlement_key(exp_txn, db_session)

    assert settlement_key == expected_settlement_key


@responses.activate
def test_get_settlement_key_with_settlement_key(db_session: db.Session) -> None:
    create_transaction_record(db_session)
    exp_txn = create_export_transaction("1234567", 10, "123456")
    expected_settlement_key = "123456"
    squaremeal = SquareMeal()
    settlement_key = squaremeal.get_settlement_key(exp_txn, db_session)

    assert settlement_key == expected_settlement_key


def test_make_export_data(db_session: db.Session):
    exp_txn = create_export_transaction("1234567", 10, "123456")
    squaremeal = SquareMeal()

    expected_result = AgentExportData(
        outputs=[
            AgentExportDataOutput(
                key="export.json",
                data={
                    "transaction_id": "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92",
                    "loyalty_id": 10,
                    "auth": True,
                    "cleared": False,
                    "mid": "1234567",
                    "transaction_date": "2022-11-01T17:14:08",
                    "transaction_amount": 5566,
                    "transaction_currency": "GBP",
                    "payment_card_account_id": 1,
                    "store_id": None,
                    "brand_id": None,
                    "payment_card_last_four": None,
                    "payment_scheme": {"slug": None, "auth_code": None, "approval_code": None},
                    "payment_card_expiry_month": None,
                    "payment_card_expiry_year": None,
                },
            )
        ],
        transactions=[
            ExportTransaction(
                id=None,
                created_at=None,
                updated_at=None,
                transaction_id="1234567",
                feed_type=FeedType.AUTH,
                provider_slug="squaremeal",
                transaction_date=pendulum.DateTime(
                    2022, 11, 1, 17, 14, 8, 838138, tzinfo=pendulum.timezone("Europe/London")
                ),
                spend_amount=5566,
                spend_currency="GBP",
                loyalty_id=10,
                mid="1234567",
                primary_identifier="test-mid-primary",
                location_id=None,
                merchant_internal_id=None,
                user_id=1,
                scheme_account_id=1,
                payment_card_account_id=1,
                credentials="something",
                auth_code=None,
                approval_code=None,
                status=None,
                settlement_key="123456",
                last_four=None,
                expiry_month=None,
                expiry_year=None,
                payment_provider_slug=None,
            )
        ],
        extra_data={},
    )

    result = squaremeal.make_export_data(exp_txn, db_session)

    assert result.outputs == expected_result.outputs
