from collections.abc import Iterable
from functools import cached_property

from app import db, tasks  # noqa
from app.core.export_director import ExportFields, create_export
from app.models import MerchantIdentifier, PaymentTransaction, TransactionStatus, UserIdentity
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
            coalesce_jobs=True,
            callback=self.load_unmatched_transactions,
            logger=self.log,
        )

        self.log.debug(f"Beginning schedule {scheduler}.")
        scheduler.run()

    def load_unmatched_transactions(self) -> None:
        with db.session_scope() as session:
            pt_updates: list = []
            for ptx, uid, mid in self.find_unmatched_transactions(session=session):
                self.create_export_transaction(ptx, uid, mid, session=session)
                pt_updates.append({"id": ptx.id, "status": TransactionStatus.MATCHED.name})

            if len(pt_updates) > 0:
                session.bulk_update_mappings(PaymentTransaction, pt_updates)

    def find_unmatched_transactions(
        self, session: db.Session
    ) -> Iterable[tuple[PaymentTransaction, UserIdentity, MerchantIdentifier]]:
        raise NotImplementedError(
            "Override the find_unmatched_transactions method in your agent to obtained unmatched transactions."
        )

    def create_export_transaction(
        self,
        transaction: PaymentTransaction,
        user_identity: UserIdentity,
        merchant_identifier: MerchantIdentifier,
        *,
        session: db.Session,
    ) -> None:
        create_export(
            ExportFields(
                transaction_id=transaction.transaction_id,
                feed_type=None,
                merchant_slug=self.provider_slug,
                transaction_date=transaction.transaction_date,
                spend_amount=transaction.spend_amount,
                spend_currency=transaction.spend_currency,
                loyalty_id=user_identity.loyalty_id,
                mid=merchant_identifier.identifier,
                primary_identifier=transaction.mid,
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
                payment_provider_slug=transaction.provider_slug,
                auth_code=transaction.auth_code,
                approval_code=transaction.approval_code,
                extra_fields=transaction.extra_fields,
            ),
            session=session,
        )
