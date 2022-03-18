from typing import cast

from sqlalchemy import any_

from app import db, models
from app.core.export_director import ExportFields, create_export
from app.feeds import FeedType
from app.registry import NoSuchAgent
from app.reporting import get_logger
from app.streaming.agents.base import BaseStreamingAgent
from app.streaming.agents.registry import streaming_agents

log = get_logger("streaming-worker")


class StreamingWorker:
    def handle_transaction(self, transaction_id: str, feed_type: FeedType, *, session: db.Session) -> None:
        def load_data():
            return (
                session.query(models.Transaction, models.UserIdentity, models.MerchantIdentifier)
                .join(
                    models.MerchantIdentifier,
                    models.MerchantIdentifier.id == any_(models.Transaction.merchant_identifier_ids),
                )
                .join(models.UserIdentity, models.UserIdentity.transaction_id == models.Transaction.transaction_id)
                .filter(
                    models.Transaction.transaction_id == transaction_id,
                    models.Transaction.feed_type == feed_type,
                )
                .one()
            )

        transaction, user_identity, merchant_identifier = db.run_query(
            load_data,
            session=session,
            read_only=True,
            description=f"load streaming data for transaction #{transaction_id}",
        )

        try:
            agent = cast(BaseStreamingAgent, streaming_agents.instantiate(transaction.merchant_slug))
        except NoSuchAgent:
            log.debug(f"No streaming agent is registered for slug {transaction.merchant_slug}.")
            return

        if agent.should_stream(transaction):
            self._handle(transaction, user_identity, merchant_identifier, session=session)

    def handle_transactions(self, match_group: str, *, session: db.Session) -> None:
        raise NotImplementedError

    def _handle(
        self,
        transaction: models.Transaction,
        user_identity: models.UserIdentity,
        merchant_identifier: models.MerchantIdentifier,
        *,
        session: db.Session,
    ) -> None:
        create_export(
            ExportFields(
                transaction_id=transaction.transaction_id,
                feed_type=transaction.feed_type,
                merchant_slug=transaction.merchant_slug,
                transaction_date=transaction.transaction_date,
                spend_amount=transaction.spend_amount,
                spend_currency=transaction.spend_currency,
                loyalty_id=user_identity.loyalty_id,
                mid=merchant_identifier.mid,
                store_id=merchant_identifier.store_id,
                brand_id=merchant_identifier.brand_id,
                user_id=user_identity.user_id,
                scheme_account_id=user_identity.scheme_account_id,
                payment_card_account_id=user_identity.payment_card_account_id,
                credentials=user_identity.credentials,
            ),
            session=session,
        )
