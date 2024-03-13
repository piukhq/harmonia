from functools import cached_property

from sqlalchemy import any_

from app import db, models, tasks  # noqa
from app.core.export_director import ExportFields, create_export
from app.models import TransactionStatus
from app.reporting import get_logger
from app.scheduler import CronScheduler
from app.utils import missing_property

log = get_logger("unmatched-transactions-base-agent")


class BaseAgent:
    def __init__(self) -> None:
        self.log = get_logger(f"unmatched-transactions-agent.{self.provider_slug}")

    @property
    def provider_slug(self) -> str:
        return missing_property(type(self), "provider_slug")

    def __repr__(self) -> str:
        return f"{type(self).__name__}(provider_slug={self.provider_slug})"

    def __str__(self) -> str:
        return f"unmatched transactions agent {type(self).__name__} for {self.provider_slug}"

    @cached_property
    def schedule(self):
        with db.session_scope() as session:
            schedule = self.config.get("schedule", session=session)
        return schedule

    def run(self) -> None:
        scheduler = CronScheduler(
            name=f"unmatched-transactions-streamer-{self.provider_slug}",
            schedule_fn=lambda: self.schedule,
            callback=self.callback,
            logger=self.log,  # type: ignore
        )

        self.log.debug(f"Beginning schedule {scheduler}.")
        scheduler.run()

    def callback(self) -> None:
        self.start_unmatched_transactions_process()

    def start_unmatched_transactions_process(self) -> None:
        with db.session_scope() as session:
            transaction_ids = self.find_unmatched_transactions(session=session)

            if transaction_ids:
                for id in transaction_ids:
                    transaction, user_identity, merchant_identifier = self.handle_transactions(id, session)

                    self.create_export_transaction(transaction, user_identity, merchant_identifier, session=session)
                    self.update_payment_transaction_status(transaction.transaction_id, session)

    def find_unmatched_transactions(self, session: db.Session) -> list[int]:
        raise NotImplementedError(
            "Override the find_unmatched_transactions method in your agent to obtained unmatched transactions."
        )

    def handle_transactions(
        self, transaction_id: int, session: db.Session
    ) -> tuple[models.Transaction, models.UserIdentity, models.MerchantIdentifier]:
        def load_data():
            return (
                session.query(models.Transaction, models.UserIdentity, models.MerchantIdentifier)
                .join(
                    models.MerchantIdentifier,
                    models.MerchantIdentifier.id == any_(models.Transaction.merchant_identifier_ids),
                )
                .join(models.UserIdentity, models.UserIdentity.transaction_id == models.Transaction.transaction_id)
                .filter(
                    models.Transaction.id == transaction_id,
                )
                .one()
            )

        transaction, user_identity, merchant_identifier = db.run_query(
            load_data,
            session=session,
            read_only=True,
            description=f"load streaming data for transaction #{transaction_id}",
        )

        return transaction, user_identity, merchant_identifier

    def create_export_transaction(
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
                merchant_slug=self.provider_slug,
                transaction_date=transaction.transaction_date,
                spend_amount=transaction.spend_amount,
                spend_currency=transaction.spend_currency,
                loyalty_id=user_identity.loyalty_id,
                mid=merchant_identifier.identifier,
                primary_identifier=transaction.mids[0],
                location_id=merchant_identifier.location_id,
                merchant_internal_id=merchant_identifier.merchant_internal_id,
                user_id=user_identity.user_id,
                scheme_account_id=user_identity.scheme_account_id,
                payment_card_account_id=user_identity.payment_card_account_id,
                credentials=user_identity.credentials,
                settlement_key=transaction.settlement_key,
                last_four=user_identity.last_four,
                expiry_month=user_identity.expiry_month,
                expiry_year=user_identity.expiry_year,
                payment_provider_slug=transaction.payment_provider_slug,
                auth_code=transaction.auth_code,
                approval_code=transaction.approval_code,
                extra_fields=transaction.extra_fields,
            ),
            session=session,
        )

    def update_payment_transaction_status(self, transaction_id: str, session: db.Session) -> None:
        payment_transaction = (
            session.query(models.PaymentTransaction)
            .filter(models.PaymentTransaction.transaction_id == transaction_id)
            .one()
        )
        payment_transaction.status = TransactionStatus.MATCHED.name
        session.commit()
