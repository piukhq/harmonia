from typing import Optional

import requests
import sentry_sdk
from sqlalchemy.orm import Query

from app import db, models, tasks
from app.reporting import get_logger
from app.service.hermes import hermes

log = get_logger("identifier")


class SchemeAccountNotFound(Exception):
    pass


def payment_card_user_info(merchant_identifier_ids: list, token: str, *, session: db.Session) -> dict:
    # TODO: this query exists in app/core/matching_worker.py:50 as well, should we combine?
    merchant_identifiers = db.run_query(
        lambda: session.query(models.MerchantIdentifier)
        .filter(models.MerchantIdentifier.id.in_(merchant_identifier_ids))
        .all(),
        session=session,
        read_only=True,
        description="find payment transaction MIDs",
    )

    slugs = {merchant_identifier.loyalty_scheme.slug for merchant_identifier in merchant_identifiers}

    # TODO: this check exists in app/core/matching_worker.py:58 as well, should we combine?
    if len(slugs) > 1:
        raise ValueError(
            f"{merchant_identifier_ids} contains multiple scheme slugs! This is likely caused by an error in the MIDs. "
            f"Conflicting slugs: {slugs}"
        )

    loyalty_scheme_slug = slugs.pop()
    json = hermes.payment_card_user_info(loyalty_scheme_slug, token)

    if token in json and json[token]["scheme_account_id"] is not None:
        return json[token]
    else:
        raise SchemeAccountNotFound


def persist_user_identity(settlement_key: str, user_info: dict, *, session: db.Session) -> models.UserIdentity:
    def add_user_identity():
        user_identity = models.UserIdentity(
            settlement_key=settlement_key,
            loyalty_id=user_info["loyalty_id"],
            scheme_account_id=user_info["scheme_account_id"],
            user_id=user_info["user_id"],
            credentials=user_info["credentials"],
            first_six=user_info["card_information"]["first_six"],
            last_four=user_info["card_information"]["last_four"],
        )

        session.add(user_identity)
        session.commit()
        return user_identity

    user_identity = db.run_query(add_user_identity, session=session, description="create user identity")
    log.debug(f"Persisted {user_identity}.")

    return user_identity


def _user_identity_query(settlement_key: int, *, session: db.Session) -> Query:
    return session.query(models.UserIdentity).filter(
        models.UserIdentity.settlement_key == settlement_key
    )


def try_get_user_identity(settlement_key: int, *, session: db.Session) -> Optional[models.UserIdentity]:
    return db.run_query(
        _user_identity_query(settlement_key, session=session).one_or_none,
        session=session,
        read_only=True,
        description="try to find user identity",
    )


def get_user_identity(settlement_key: int, *, session: db.Session) -> models.UserIdentity:
    return db.run_query(
        _user_identity_query(settlement_key, session=session).one,
        session=session,
        read_only=True,
        description="find user identity",
    )


def identify_payment_transaction(payment_transaction_id: int, *, session: db.Session) -> None:
    log.debug(f"Attempting identification of payment transaction #{payment_transaction_id}")

    payment_transaction = db.run_query(
        lambda: session.query(models.PaymentTransaction).get(payment_transaction_id),
        session=session,
        read_only=True,
        description="find payment transaction",
    )

    if payment_transaction is None:
        log.warning(f"Failed to load payment transaction #{payment_transaction_id} - record may have been deleted.")
        return

    if try_get_user_identity(payment_transaction, session=session):
        log.warning(f"Skipping identification of {payment_transaction} as it already has an associated user identity.")
        return

    try:
        user_info = payment_card_user_info(payment_transaction, session=session)
    except SchemeAccountNotFound:
        log.debug(f"Hermes was unable to find a scheme account matching {payment_transaction}")
        return
    except requests.RequestException:
        event_id = sentry_sdk.capture_exception()
        log.debug(f"Failed to get user info from Hermes. Task will be requeued. Sentry event ID: {event_id}")
        tasks.matching_queue.enqueue(tasks.identify_payment_transaction, payment_transaction_id)
        return

    if "card_information" not in user_info:
        log.debug(f"Hermes identified {payment_transaction} but could return no payment card information")
        return

    persist_user_identity(payment_transaction, user_info, session=session)

    log.debug("Identification complete. Enqueueing matching task.")

    tasks.matching_queue.enqueue(tasks.match_payment_transaction, payment_transaction_id)


def identify_user(settlement_key: str, merchant_identifier_ids: list, token: str, *, session: db.Session) -> None:
    log.debug(f"Attempting identification of a transaction with settlement_key #{settlement_key}")

    if try_get_user_identity(settlement_key, session=session):
        log.warning(f"Skipping identification of {settlement_key} as it already has an associated user identity.")
        return

    try:
        user_info = payment_card_user_info(merchant_identifier_ids, token, session=session)
    except SchemeAccountNotFound:
        log.debug(f"Hermes was unable to find a scheme account for transaction with settlement Key:  {settlement_key}")
        return
    except requests.RequestException:
        event_id = sentry_sdk.capture_exception()
        log.debug(f"Failed to get user info from Hermes. Task will be requeued. Sentry event ID: {event_id}")
        tasks.identify_user_queue.enqueue(tasks.identify_user, settlement_key, merchant_identifier_ids, token)
        return

    if "card_information" not in user_info:
        log.debug(f"Hermes identified {settlement_key} but could return no payment card information")
        return

    persist_user_identity(settlement_key, user_info, session=session)

    log.debug("Identification complete. Enqueueing matching task.")
