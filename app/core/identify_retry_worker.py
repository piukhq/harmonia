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

    def tick(self) -> None:
        unidentified_transactions = db.run_query(
            lambda: db.session.query(models.MatchedTransaction).filter(
                models.MatchedTransaction.user_identity_id.is_(None)
            )
        )

        self.log.debug(f"Found {unidentified_transactions.count()} unidentified matched transactions.")

        for transaction in unidentified_transactions:
            tasks.matching_queue.enqueue(tasks.identify_matched_transaction, transaction.id)
