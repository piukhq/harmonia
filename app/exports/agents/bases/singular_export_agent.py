import typing as t
from contextlib import ExitStack, contextmanager

import humanize
import pendulum
import sentry_sdk
from requests import RequestException, Response

from app import db, models
from app.exports import models as exp_model
from app.exports.agents import BaseAgent
from app.exports.agents.bases.base import AgentExportData
from app.exports.exceptions import MissingExportData
from app.prometheus import bink_prometheus


class SingularExportAgent(BaseAgent):
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

    def get_retry_datetime(
        self, retry_count: int, *, exception: t.Optional[Exception] = None
    ) -> t.Optional[pendulum.DateTime]:
        """
        Given a number of previous retries, return the timepoint at which an export should be retried.
        The return value is optional - by returning `None` an agent can indicate that the export should not be retried.

        The default settings are to retry after 20 minutes up to 4 times, and then stop.

        Derived agents may override this method to provide custom retry behaviour.
        """
        return SingularExportAgent.simple_retry(retry_count, delay=pendulum.duration(minutes=20), max_tries=4)

    def run(self):
        raise NotImplementedError(
            f"{type(self).__name__} is a singular export agent and as such must be run via the export worker."
        )

    def export(self, export_data: AgentExportData, *, retry_count: int = 0, session: db.Session) -> None:
        raise NotImplementedError(
            "Override the export method in your agent to act as the entry point into the singular export process."
        )

    def export_all(self, *, session: db.Session) -> None:
        raise NotImplementedError(
            f"{type(self).__name__} is a singular export agent and as such does not support batch exports."
        )

    def find_export_transaction(
        self, pending_export: models.PendingExport, *, session: db.Session
    ) -> models.ExportTransaction:
        def find_transaction():
            return session.query(models.ExportTransaction).get(pending_export.export_transaction_id)

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
        self.log.info(f"Handling {pending_export}.")

        try:
            export_transaction = self.find_export_transaction(pending_export, session=session)
        except db.NoResultFound:
            self.log.warning(
                f"The export agent failed to load its matched transaction. {pending_export} will be discarded."
            )
            self._delete_pending_export(pending_export, session=session)
            return

        self.log.info(f"{type(self).__name__} handling {export_transaction}.")
        try:
            export_data = self.make_export_data(export_transaction, session)
        except MissingExportData:
            sentry_sdk.capture_message(
                f"The export transaction {export_transaction} has missing data and cannot "
                f"be exported. {pending_export} will be discarded."
            )
            export_transaction.status = exp_model.ExportTransactionStatus.EXPORT_FAILED
            self._delete_pending_export(pending_export, session=session)
            return

        try:
            self._send_export_data(export_data, retry_count=pending_export.retry_count, session=session)
        except Exception as ex:
            event_id = sentry_sdk.capture_exception()

            retry_at = self.get_retry_datetime(pending_export.retry_count, exception=ex)

            if retry_at:
                retry_humanized = humanize.naturaltime(retry_at.naive())
                self.log.warning(
                    f"Singular export raised exception: {repr(ex)}. Sentry event ID: {event_id} "
                    f"This operation will be retried {retry_humanized} at {retry_at}."
                )
                self._retry_pending_export(pending_export, retry_at, session=session)
                return
            else:
                self.log.warning(
                    f"Singular export raised exception: {repr(ex)}. Sentry event ID: {event_id} "
                    "This operation has exceeded its retry limit and will be discarded."
                )
                export_transaction.status = exp_model.ExportTransactionStatus.EXPORT_FAILED
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
        with self._update_metrics(export_data=export_data, session=session):
            self.export(export_data, retry_count=retry_count, session=session)

            self._save_export_transactions(export_data, session=session)

    def _delete_pending_export(self, pending_export: models.PendingExport, *, session: db.Session) -> None:
        self.log.info(f"Removing pending export {pending_export}.")

        def delete_pending_export():
            session.delete(pending_export)
            session.commit()

        db.run_query(delete_pending_export, session=session, description="delete pending export")

    def get_response_result(self, response: Response) -> t.Optional[str]:
        """
        Override in your agent to get an error code/message from the given response.
        """
        return None

    def _try_get_result_from_exception(self, ex: Exception) -> str:
        """
        If the given exception is a request exception and we can get a response result from it, return the result.
        Otherwise, if anything is missing or any exception is raised, return a blank string.
        This is used for the response_result label in the failed_requests metric for Prometheus.
        """
        try:
            if isinstance(ex, RequestException) and ex.response is not None:
                response_result = self.get_response_result(ex.response)
                if response_result is not None:
                    return response_result
        except Exception:
            pass
        return ""

    @contextmanager
    def _update_metrics(self, export_data: AgentExportData, session: db.Session) -> t.Iterator[None]:
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
            except Exception as ex:
                self.bink_prometheus.increment_counter(
                    agent=self,
                    counter_name="failed_requests",
                    increment_by=1,
                    process_type="export",
                    slug=self.provider_slug,
                    response_result=self._try_get_result_from_exception(ex),
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

    def make_export_data(self, matched_transaction: models.MatchedTransaction, session: db.Session) -> AgentExportData:
        raise NotImplementedError("Override the make export data method in your export agent")
