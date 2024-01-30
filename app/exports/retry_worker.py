import humanize
import pendulum
from sqlalchemy import and_, or_, orm

from app import db, models, tasks
from app.reporting import get_logger
from app.scheduler import CronScheduler


class ExportRetryWorker:
    def __init__(self) -> None:
        self.log = get_logger("retry-worker")
        self.scheduler = CronScheduler(
            name="export-retry", schedule_fn=self._get_schedule, callback=self._tick, logger=self.log
        )

    def _get_schedule(self) -> str:
        return "* * * * *"

    def _tick(self) -> None:
        with db.session_scope() as session:

            def find_pending_exports():
                now = pendulum.now("UTC")
                yesterday = now.subtract(hours=24)
                return (
                    session.query(models.PendingExport)
                    .filter(
                        or_(
                            and_(
                                models.PendingExport.retry_at.isnot(None),
                                models.PendingExport.retry_at <= now,
                            ),
                            and_(
                                models.PendingExport.retry_at.is_(None),
                                models.PendingExport.created_at <= yesterday,
                                or_(
                                    models.PendingExport.updated_at.is_(None),
                                    models.PendingExport.updated_at <= yesterday,
                                ),
                            ),
                        )
                    )
                    .all()
                )

            pending_exports = db.run_query(
                find_pending_exports,
                session=session,
                read_only=True,
                description="find pending exports for retry",
            )

            if not pending_exports:
                return

            pending_exports_count = len(pending_exports)
            self.log.info(f"Found {pending_exports_count} pending exports for retry.")

            def requeue_pending_exports():
                for pending_export in pending_exports:
                    # if retry_at is already null we assume this is a "missed" export that just needs requeueing.
                    if pending_export.retry_at is None:
                        # we still commit a change to [re]set the updated_at field.
                        pending_export.retry_at = None
                        orm.attributes.flag_modified(pending_export, "retry_at")
                        self.log.info(f"{pending_export} was missed and will be requeued.")
                    # otherwise we increment the retry count & nullify retry_at.
                    else:
                        # nullifying the retry_at means the scheduler won't retry the transaction
                        # until a new retry date is set on it.
                        # this helps to prevent race conditions without needing locks.
                        pending_export.retry_count += 1
                        pending_export.retry_at = None
                        self.log.info(f"{pending_export} is ready for retry.")

                session.commit()

            db.run_query(requeue_pending_exports, session=session, description="requeue pending exports")

            for pending_export in pending_exports:
                tasks.export_queue.enqueue(tasks.export_singular_transaction, pending_export.id)
                self.log.debug(
                    f"Requeued {pending_export} for its {humanize.ordinal(pending_export.retry_count)} retry."
                )

            self.log.info(f"{pending_exports_count} pending exports requeued and updated.")

    def run(self) -> None:
        self.log.debug(f'Export retry worker scheduler starting up with schedule "{self._get_schedule()}".')
        self.scheduler.run()
