import typing as t
from collections.abc import Iterable
from functools import cached_property
from pathlib import Path

import pendulum

import settings
from app import config, db
from app.export_result.agents.bases.base import BaseAgent
from app.imports.agents.bases.file_agent import BlobFileSource, FileSourceBase, LocalFileSource
from app.prometheus import bink_prometheus
from app.scheduler import CronScheduler
from app.service.atlas import AuditTransaction


class ResultsFileAgent(BaseAgent):
    config = config.Config()  # override this

    def __init__(self):
        super().__init__()
        self.bink_prometheus = bink_prometheus

    def format_audit_transaction(self, data: dict) -> list[AuditTransaction]:
        raise NotImplementedError

    def yield_results_data(self, data: bytes) -> Iterable[dict]:
        raise NotImplementedError

    def _load_results(self, data: bytes, source: str):
        self.log.info(f"Loading export results for {self.provider_slug}")

        results_data = []
        for result in self.yield_results_data(data):
            results_data.append(result)
            yield

        total_unique_results = self._load_export_results(
            results_data, export_transaction_callback=self.format_audit_transaction, source=source
        )

        self.log.info(f"Number of export results for {self.provider_slug}: {total_unique_results}")
        self._update_file_metrics(timestamp=pendulum.now().timestamp())

    _FileAgentConfig = t.NamedTuple("_FileAgentConfig", [("path", str), ("schedule", str)])

    def _update_file_metrics(self, timestamp: float) -> None:
        """
        Update any Prometheus metrics this agent might have
        """
        self.bink_prometheus.increment_counter(
            agent=self,
            counter_name="files_received",
            increment_by=1,
            process_type="results",
            slug=self.provider_slug,
        )
        self.bink_prometheus.update_gauge(
            agent=self,
            gauge_name="last_file_timestamp",
            value=timestamp,
            process_type="results",
            slug=self.provider_slug,
        )

    @cached_property
    def fileagent_config(self) -> _FileAgentConfig:
        with db.session_scope() as session:
            path = self.config.get("path", session=session)
            schedule = self.config.get("schedule", session=session)
        return self._FileAgentConfig(path, schedule)

    @cached_property
    def filesource(self) -> FileSourceBase:
        filesource_class: type[FileSourceBase] = BlobFileSource if settings.BLOB_STORAGE_DSN else LocalFileSource
        return filesource_class(Path(self.fileagent_config.path), logger=self.log)

    def run(self) -> None:
        self.log.info(
            f"Watching {self.filesource.path} for export result files via {self.filesource.__class__.__name__}."
        )

        name = f"{self.provider_slug}-export-result-load"
        self.log.info(f"Using leader election name: {name}")
        scheduler = CronScheduler(
            name=name,
            schedule_fn=lambda: self.fileagent_config.schedule,
            callback=self.callback,
            coalesce_jobs=True,
            logger=self.log,
        )

        self.log.debug(f"Beginning {scheduler}.")
        scheduler.run()

    def callback(self):
        self.filesource.provide(self._load_results)
