import requests

from app.reporting import get_logger
from app import models, db, tasks
from app.service.hermes import hermes


log = get_logger("identifier")


class HermesRequestFailed(Exception):
    pass


class SchemeAccountNotFound(Exception):
    pass


class Identifier:
    def payment_card_user_info(
        self, matched_transaction: models.MatchedTransaction
    ) -> dict:
        loyalty_scheme_slug = (
            matched_transaction.merchant_identifier.loyalty_scheme.slug
        )

        resp = hermes.payment_card_user_info(
            loyalty_scheme_slug, matched_transaction.card_token
        )

        log.debug(
            f"Hermes identification request responded with {resp.status_code} {resp.reason}"
        )

        try:
            resp.raise_for_status()
        except Exception as ex:
            raise HermesRequestFailed from ex

        json = resp.json()
        if matched_transaction.card_token in json:
            return json[matched_transaction.card_token]
        else:
            raise SchemeAccountNotFound

    def persist_user_identity(
        self, matched_transaction: models.MatchedTransaction, user_info: dict
    ) -> None:
        user_identity = models.UserIdentity(
            loyalty_id=user_info["loyalty_id"],
            scheme_account_id=user_info["scheme_account_id"],
            user_id=user_info["user_id"],
            credentials=user_info["credentials"],
            matched_transaction_id=matched_transaction.id,
        )

        log.debug(f"Persisting {user_identity}.")

        db.session.add(user_identity)
        db.session.commit()

    def identify_matched_transaction(self, matched_transaction_id: int) -> None:
        log.debug(
            f"Attempting identification of matched transaction #{matched_transaction_id}"
        )
        matched_transaction = db.session.query(models.MatchedTransaction).get(
            matched_transaction_id
        )

        if matched_transaction.user_identity is not None:
            log.warning(
                f"Skipping identification of matched transaction #{matched_transaction_id} as it already has an "
                "associated user identity."
            )
            return

        try:
            user_info = self.payment_card_user_info(matched_transaction)
        except requests.RequestException:
            log.debug("Failed to get user info from Hermes.")
            return

        self.persist_user_identity(matched_transaction, user_info)

        log.debug("Identification complete. Enqueueing export task.")

        tasks.export_queue.enqueue(
            tasks.export_matched_transaction, matched_transaction_id
        )
