from functools import cached_property
from app import scheduler, reporting, config, models, db, tasks


SCHEDULE_KEY = f"{config.KEY_PREFIX}identify-retry.schedule"


class IdentifyRetryWorker:
    config = config.Config(config.ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *"))

    def __init__(self):
        self.log = reporting.get_logger("identify-retry")
        self.scheduler = scheduler.CronScheduler(
            name="identify-retry", schedule_fn=lambda: self.schedule, callback=self.tick, logger=self.log
        )

    def run(self) -> None:
        self.scheduler.run()

    @cached_property
    def schedule(self) -> str:
        with db.session_scope() as session:
            schedule = self.config.get("schedule", session=session)
        return schedule

    def tick(self, *, session: db.Session) -> None:
        unidentified_transactions = db.run_query(
            lambda: session.query(models.PaymentTransaction)
            .filter(models.PaymentTransaction.user_identity_id.is_(None))
            .all(),
            session=session,
            read_only=True,
            description="find unidentified payment transactions",
        )

        self.log.debug(f"Found {len(unidentified_transactions)} unidentified payment transactions.")

        for transaction in unidentified_transactions:
            tasks.matching_queue.enqueue(tasks.identify_payment_transaction, transaction.id)
