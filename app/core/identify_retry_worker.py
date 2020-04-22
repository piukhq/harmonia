from app import scheduler, reporting, config, models, db, tasks


SCHEDULE_KEY = f"{config.KEY_PREFIX}identify-retry.schedule"


class IdentifyRetryWorker:
    class Config:
        schedule = config.ConfigValue(SCHEDULE_KEY, "* * * * *")

    def __init__(self):
        self.log = reporting.get_logger("identify-retry")
        self.scheduler = scheduler.CronScheduler(schedule_fn=self.get_schedule, callback=self.tick, logger=self.log)

    def run(self) -> None:
        self.scheduler.run()

    def get_schedule(self) -> str:
        return self.Config.schedule

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
