import requests
import sentry_sdk

from app.reporting import get_logger
from app import models, db, tasks
from app.service.hermes import hermes


log = get_logger("identifier")


class SchemeAccountNotFound(Exception):
    pass


class Identifier:
    def payment_card_user_info(self, payment_transaction: models.PaymentTransaction) -> dict:
        # TODO: this query exists in app/core/matching_worker.py:50 as well, should we combine?
        merchant_identifiers = db.run_query(
            lambda: db.session.query(models.MerchantIdentifier)
            .filter(models.MerchantIdentifier.id.in_(payment_transaction.merchant_identifier_ids))
            .all(),
            description="find payment transaction MIDs",
        )

        slugs = {merchant_identifier.loyalty_scheme.slug for merchant_identifier in merchant_identifiers}

        # TODO: this check exists in app/core/matching_worker.py:58 as well, should we combine?
        if len(slugs) > 1:
            raise ValueError(
                f"{payment_transaction} contains multiple scheme slugs! This is likely caused by an error in the MIDs. "
                f"Conflicting slugs: {slugs}"
            )

        loyalty_scheme_slug = slugs.pop()

        token = payment_transaction.card_token
        json = hermes.payment_card_user_info(loyalty_scheme_slug, token)

        if token in json and json[token]["scheme_account_id"] is not None:
            return json[token]
        else:
            raise SchemeAccountNotFound

    def persist_user_identity(self, payment_transaction: models.PaymentTransaction, user_info: dict) -> None:
        def add_user_identity():
            user_identity = models.UserIdentity(
                loyalty_id=user_info["loyalty_id"],
                scheme_account_id=user_info["scheme_account_id"],
                user_id=user_info["user_id"],
                credentials=user_info["credentials"],
                first_six=user_info["card_information"]["first_six"],
                last_four=user_info["card_information"]["last_four"],
            )

            payment_transaction.user_identity = user_identity

            db.session.add(user_identity)
            db.session.commit()
            return user_identity

        user_identity = db.run_query(add_user_identity, description="create user identity")
        log.debug(f"Persisted {user_identity}.")

    def identify_payment_transaction(self, payment_transaction_id: int) -> None:
        log.debug(f"Attempting identification of payment transaction #{payment_transaction_id}")

        payment_transaction = db.run_query(
            lambda: db.session.query(models.PaymentTransaction).get(payment_transaction_id),
            description="find payment transaction",
        )

        if payment_transaction.user_identity is not None:
            log.warning(
                f"Skipping identification of {payment_transaction} as it already has an associated user identity."
            )
            return

        try:
            user_info = self.payment_card_user_info(payment_transaction)
        except SchemeAccountNotFound:
            log.debug(f"Hermes was unable to find a scheme amount matching {payment_transaction}")
            return
        except requests.RequestException:
            event_id = sentry_sdk.capture_exception()
            log.debug(f"Failed to get user info from Hermes. Sentry event ID: {event_id}")
            return

        if "card_information" not in user_info:
            log.debug(f"Hermes identified {payment_transaction} but could return no payment card information")
            return

        self.persist_user_identity(payment_transaction, user_info)

        log.debug("Identification complete. Enqueueing matching task.")

        tasks.matching_queue.enqueue(tasks.match_payment_transaction, payment_transaction_id)
