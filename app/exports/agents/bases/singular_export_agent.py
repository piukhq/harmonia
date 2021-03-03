import typing as t
from contextlib import ExitStack, contextmanager

import pendulum
import humanize

import settings
from app import db, models
from app.exports.agents import BaseAgent
from app.exports.agents.bases.base import AgentExportData
from app.prometheus import bink_prometheus
from app.service import atlas
from app.status import status_monitor


class SingularExportAgent(BaseAgent):
    class ReceiptNumberNotFound(Exception):
        pass

    def __init__(self):
        super().__init__()

        self.bink_prometheus = bink_prometheus

    @staticmethod
    def simple_retry(retry_count: int, *, delay: pendulum.Duration, max_tries: int) -> t.Optional[pendulum.DateTime]:
        """
        Returns now() + `delay` if retry_count is less than `max_tries`, otherwise null
        """
        if retry_count < max_tries:
            return pendulum.now() + delay
        else:
            return None

    def get_retry_datetime(self, retry_count: int) -> t.Optional[pendulum.DateTime]:
        """
        Given a number of previous retries, return the timepoint at which an export should be retried.
        The return value is optional - by returning `None` an agent can indicate that the export should not be retried.

        The default settings are to retry after 20 minutes up to 4 times, and then stop.

        Derived agents may override this method to provide custom retry behaviour.
        """
        return SingularExportAgent.simple_retry(retry_count, delay=pendulum.duration(minutes=20), max_tries=4)

    def run(self):
        raise NotImplementedError(
            f"{type(self).__name__} is a singular export agent and as such must be run via the import director."
        )

    def export(
        self, export_data: AgentExportData, *, retry_count: int = 0, session: db.Session
    ) -> atlas.MessagePayload:
        raise NotImplementedError(
            "Override the export method in your agent to act as the entry point into the singular export process."
        )

    def export_all(self, *, session: db.Session):
        raise NotImplementedError(
            f"{type(self).__name__} is a singular export agent and as such does not support batch exports."
        )

    def find_matched_transaction(
        self, pending_export: models.PendingExport, *, session: db.Session
    ) -> models.MatchedTransaction:
        def find_transaction():
            return session.query(models.MatchedTransaction).get(pending_export.matched_transaction_id)

        matched_transaction = db.run_query(
            find_transaction,
            session=session,
            read_only=True,
            description="load matched transaction",
        )

        if matched_transaction is None:
            self.log.warning(
                f"Failed to load matched transaction #{pending_export.matched_transaction_id}. "
                "Record may have been deleted."
            )
            raise db.NoResultFound

        return matched_transaction

    def handle_pending_export(self, pending_export: models.PendingExport, *, session: db.Session):
        status_monitor.checkin(self)

        self.log.info(f"Handling {pending_export}.")

        try:
            matched_transaction = self.find_matched_transaction(pending_export, session=session)
        except db.NoResultFound:
            self.log.warning(
                f"The export agent failed to load its matched transaction. {pending_export} will be discarded."
            )
            self._delete_pending_export(pending_export, session=session)
            return

        self.log.info(f"{type(self).__name__} handling {matched_transaction}.")
        export_data = self.make_export_data(matched_transaction)

        try:
            self._send_export_data(export_data, retry_count=pending_export.retry_count, session=session)
        except Exception as ex:
            retry_at = self.get_retry_datetime(pending_export.retry_count)

            if retry_at:
                retry_humanized = humanize.naturaltime(retry_at.naive())
                self.log.warning(
                    f"Singular export raised exception: {repr(ex)}. "
                    f"This operation will be retried {retry_humanized} at {retry_at}."
                )
                self._retry_pending_export(pending_export, retry_at, session=session)
                return
            else:
                self.log.warning(
                    f"Singular export raised exception: {repr(ex)}. "
                    "This operation has exceeded its retry limit and will be discarded."
                )
                matched_transaction.status = models.MatchedTransactionStatus.EXPORT_FAILED
                #  session.commit()     # this is unnecessary as _delete_pending_export will commit right after

        # if we get here, we either exported successfully or have run out of retries.
        self._delete_pending_export(pending_export, session=session)

    def _retry_pending_export(
        self, pending_export: models.PendingExport, retry_at: pendulum.DateTime, *, session: db.Session
    ) -> None:
        def set_retry_fields():
            pending_export.retry_at = retry_at
            session.commit()

        db.run_query(set_retry_fields, session=session, description="set pending export retry fields")

    def _send_export_data(self, export_data: AgentExportData, *, retry_count: int = 0, session: db.Session) -> None:
        with self._update_metrics(export_data=export_data, session=session, retry_count=retry_count):
            audit_message = self.export(export_data, retry_count=retry_count, session=session)
            if settings.AUDIT_EXPORTS:
                atlas.queue_audit_message(audit_message)

        self._save_export_transactions(export_data, session=session)

    def _delete_pending_export(self, pending_export: models.PendingExport, *, session: db.Session) -> None:
        self.log.info(f"Removing pending export {pending_export}.")

        def delete_pending_export():
            session.delete(pending_export)
            session.commit()

        db.run_query(delete_pending_export, session=session, description="delete pending export")

    @contextmanager
    def _update_metrics(self, export_data: AgentExportData, session: db.Session, retry_count: int) -> t.Iterator[None]:
        """
        Update any Prometheus metrics this agent might have
        """
        # Use the Prometheus request latency context manager if we have one. This must be the first method
        # call of course
        with ExitStack() as stack:
            self.bink_prometheus.use_histogram_context_manager(
                agent=self,
                histogram_name="request_latency",
                context_manager_stack=stack,
                process_type="export",
                slug=self.provider_slug,
            )
            self.bink_prometheus.increment_counter(
                agent=self,
                counter_name="requests_sent",
                increment_by=1,
                process_type="export",
                slug=self.provider_slug,
            )
            try:
                yield
            except self.ReceiptNumberNotFound:  # Log the more specific exception first
                self.bink_prometheus.increment_counter(
                    agent=self,
                    counter_name="failed_retried_transactions",
                    increment_by=1,
                    process_type="export",
                    slug=self.provider_slug,
                    retry_count=retry_count,
                )
                raise
            except Exception:  # Log generic exceptions as failed requests
                self.bink_prometheus.increment_counter(
                    agent=self,
                    counter_name="failed_requests",
                    increment_by=1,
                    process_type="export",
                    slug=self.provider_slug,
                )
                raise
            else:
                self.bink_prometheus.increment_counter(
                    agent=self,
                    counter_name="transactions",
                    increment_by=1,
                    process_type="export",
                    slug=self.provider_slug,
                )

    def make_export_data(self, matched_transaction: models.MatchedTransaction) -> AgentExportData:
        raise NotImplementedError("Override the make export data method in your export agent")
