import requests
import sentry_sdk

from app.reporting import get_logger
from app import models, db, tasks
from app.service.hermes import hermes


log = get_logger("identifier")


class SchemeAccountNotFound(Exception):
    pass


class Identifier:
    def payment_card_user_info(self, matched_transaction: models.MatchedTransaction) -> dict:
        loyalty_scheme_slug = matched_transaction.merchant_identifier.loyalty_scheme.slug

        json = hermes.payment_card_user_info(loyalty_scheme_slug, matched_transaction.card_token)

        if matched_transaction.card_token in json:
            return json[matched_transaction.card_token]
        else:
            raise SchemeAccountNotFound

    def persist_user_identity(self, matched_transaction: models.MatchedTransaction, user_info: dict) -> None:
        user_identity = models.UserIdentity(
            loyalty_id=user_info["loyalty_id"],
            scheme_account_id=user_info["scheme_account_id"],
            user_id=user_info["user_id"],
            credentials=user_info["credentials"],
        )

        matched_transaction.user_identity = user_identity

        db.session.add(user_identity)
        db.session.commit()

        log.debug(f"Persisted {user_identity}.")

    def identify_matched_transaction(self, matched_transaction_id: int) -> None:
        log.debug(f"Attempting identification of matched transaction #{matched_transaction_id}")
        matched_transaction = db.session.query(models.MatchedTransaction).get(matched_transaction_id)

        if matched_transaction.user_identity is not None:
            log.warning(
                "Skipping identification of matched transaction "
                f"#{matched_transaction_id} as it already has an "
                "associated user identity."
            )
            return

        try:
            user_info = self.payment_card_user_info(matched_transaction)
        except requests.RequestException:
            event_id = sentry_sdk.capture_exception()
            log.debug(f"Failed to get user info from Hermes. Sentry event ID: {event_id}")
            return

        self.persist_user_identity(matched_transaction, user_info)

        log.debug("Identification complete. Enqueueing export task.")

        tasks.export_queue.enqueue(tasks.export_matched_transaction, matched_transaction_id)
