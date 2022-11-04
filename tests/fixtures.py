import pendulum

from app import db, models
from app.feeds import FeedType


def create_transaction_record(
    session: db.Session,
    transaction_id: str,
    feed_type: FeedType = FeedType.AUTH,
    status: str = "IMPORTED",
    merchant_identifier_ids: list[int] = [1],
    primary_identifier: str = "test_primary_identifier",
    merchant_slug: str = "Bpl-Trenette",
    payment_provider_slug: str = "amex",
    match_group: str = "98765",
    transaction_date: pendulum.DateTime = pendulum.now(),
    spend_amount: int = 5566,
    spend_multiplier: int = 1,
    spend_currency: str = "GBR",
    **kwargs
) -> models.Transaction:
    transaction, _ = db.get_or_create(
        models.Transaction,
        transaction_id=transaction_id,
        feed_type=feed_type,
        defaults=dict(
            status=status,
            merchant_identifier_ids=merchant_identifier_ids,
            primary_identifier=primary_identifier,
            merchant_slug=merchant_slug,
            payment_provider_slug=payment_provider_slug,
            match_group=match_group,
            transaction_date=transaction_date,
            spend_amount=spend_amount,
            spend_multiplier=spend_multiplier,
            spend_currency=spend_currency,
            **kwargs
        ),
        session=session,
    )
    return transaction


def create_export_transaction(
    transaction_id: str,
    merchant_slug: str = "Bpl-Trenette",
    transaction_date: pendulum.DateTime = pendulum.now(),
    spend_amount: int = 5566,
    spend_currency: str = "GBR",
    loyalty_id: str = "test_loyalty_id",
    mid: str = "test_primary_identifier",
    primary_identifier: str = "test_primary_identifier",
    user_id: int = 1,
    scheme_account_id: int = 1,
    credentials: str = "something",
    **kwargs
) -> models.ExportTransaction:
    return models.ExportTransaction(
        transaction_id=transaction_id,
        provider_slug=merchant_slug,
        transaction_date=transaction_date,
        spend_amount=spend_amount,
        spend_currency=spend_currency,
        loyalty_id=loyalty_id,
        mid=mid,
        primary_identifier=primary_identifier,
        user_id=user_id,
        scheme_account_id=scheme_account_id,
        credentials=credentials,
        **kwargs
    )
