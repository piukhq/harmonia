import datetime
import logging
import shutil
import stat
import time
import typing as t
from functools import cached_property, partial
from pathlib import Path

import humanize
import pendulum
import settings
from app import db, reporting, retry, tasks
from app.imports.agents import BaseAgent
from app.prometheus import BinkPrometheus
from app.scheduler import CronScheduler
from app.service.sftp import SFTP, SFTPCredentials
from azure.core.exceptions import HttpResponseError, ResourceExistsError
from azure.storage.blob import BlobServiceClient

logging.getLogger("azure").setLevel(logging.CRITICAL)


class FileSourceBase:
    def __init__(self, path: Path, *, logger: logging.Logger) -> None:
        self.path = path
        self.log = logger
        self.bink_prometheus = BinkPrometheus()

    def provide(self, callback: t.Callable) -> None:
        raise NotImplementedError(f"{type(self).__name__} does not implement provide()")

    def _update_metrics(self, file_attr) -> None:
        """
        Update (optional) Prometheus metrics
        """
        self.bink_prometheus.increment_counter(
            agent=self,
            counter_name="files_received_counter",
            increment_by=1,
            transaction_type=self.feed_type,
            process_type="import",
            slug=self.provider_slug,
        )
        self.bink_prometheus.update_gauge(
            agent=self,
            gauge_name="last_file_timestamp_gauge",
            value=file_attr.st_mtime,
            transaction_type=self.feed_type,
            process_type="import",
            slug=self.provider_slug,
        )
        # BinkPrometheus.increment_counter(agent=self, counter_name="files_received_counter", increment_by=1)
        # BinkPrometheus.update_gauge(obj=self, gauge_name="last_file_timestamp_gauge", value=file_attr.st_mtime)


class LocalFileSource(FileSourceBase):
    def __init__(self, path: Path, *, logger: logging.Logger) -> None:
        super().__init__(settings.LOCAL_IMPORT_BASE_PATH / "imports" / path, logger=logger)

    def archive(self, filepath: Path) -> None:
        subpath = filepath.relative_to(self.path)
        archive_path = settings.LOCAL_IMPORT_BASE_PATH / Path("archives") / pendulum.today().to_date_string() / subpath
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(filepath), archive_path)

    def provide(self, callback: t.Callable) -> None:
        for filepath in (p for p in self.path.iterdir() if p.is_file() and not p.name.startswith(".")):
            with open(filepath, "rb") as f:
                data = f.read()
            try:
                for _ in callback(data=data, source=str(filepath)):
                    pass  # callback is a generator object
            except Exception as ex:
                if settings.DEBUG:
                    raise
                else:
                    self.log.error(f"File source callback {callback} for file {filepath} failed: {ex}")
            else:
                self.archive(filepath)


class BlobFileArchiveMixin:
    def archive(
        self,
        blob_name: str,
        blob_content: bytes,
        *,
        delete_callback: t.Callable,
        logger: logging.Logger,
        bbs: t.Optional[BlobServiceClient] = None,
    ) -> None:
        if not bbs:
            bbs = BlobServiceClient.from_connection_string(settings.BLOB_STORAGE_DSN)

        archive_container = f"archive-{pendulum.today().to_date_string()}"
        try:
            bbs.create_container(archive_container)
        except ResourceExistsError:
            pass  # this is fine

        try:
            bbs.get_blob_client(archive_container, blob_name).upload_blob(blob_content)
        except ResourceExistsError:
            logger.warning(f"Failed to archive {blob_name} as this blob already exists in the archive.")

        delete_callback()


class BlobFileSource(FileSourceBase, BlobFileArchiveMixin):
    container_name = "import"

    def __init__(self, path: Path, *, logger: logging.Logger) -> None:
        super().__init__(path, logger=logger)
        self.log = reporting.get_logger("blob-file-source")
        self._bbs = BlobServiceClient.from_connection_string(settings.BLOB_STORAGE_DSN)

    def provide(self, callback: t.Callable[..., t.Iterable[None]]) -> None:
        try:
            self._bbs.create_container(self.container_name)
        except ResourceExistsError:
            pass  # this is fine

        container = self._bbs.get_container_client(self.container_name)
        for blob in container.list_blobs(name_starts_with=self.path):
            blob_client = self._bbs.get_blob_client(self.container_name, blob.name)

            try:
                lease = blob_client.acquire_lease(lease_duration=60)
                lease_time = pendulum.now()
            except HttpResponseError:
                self.log.debug(f"Skipping blob {blob.name} as we could not acquire a lease.")
                continue

            content = blob_client.download_blob(lease=lease).readall()

            self.log.debug(f"Invoking callback for blob {blob.name}.")

            try:
                for _ in callback(data=content, source=f"{self.container_name}/{blob.name}"):
                    lease_length = pendulum.now().diff(lease_time).in_seconds()
                    if lease_length > 30:
                        lease.renew()
            except Exception as ex:
                if settings.DEBUG:
                    raise
                else:
                    self.log.error(f"File source callback {callback} for blob {blob.name} failed: {ex}.")
            else:
                self.archive(
                    blob.name,
                    content,
                    delete_callback=partial(blob_client.delete_blob, lease=lease),
                    bbs=self._bbs,
                    logger=self.log,
                )


class SftpFileSource(FileSourceBase, BlobFileArchiveMixin):
    def __init__(
        self, credentials: SFTPCredentials, skey: t.Optional[str], path: Path, *, logger: logging.Logger
    ) -> None:
        super().__init__(path, logger=logger)
        self.credentials = credentials
        self.skey = skey
        self.log = reporting.get_logger("sftp-file-source")

    def provide(self, callback: t.Callable[..., t.Iterable[None]]) -> None:
        with SFTP(self.credentials, self.skey, str(self.path)) as sftp:
            listing = sftp.client.listdir_attr()
            for file_attr in listing:
                if not stat.S_ISDIR(file_attr.st_mode):
                    try:
                        with sftp.client.file(file_attr.filename, "r") as f:
                            data = f.read()
                            # Opportunity to check the file hash here with f.check()
                            # but as per Paramiko docs: "Many (most?) servers don’t
                            # support this extension yet."
                    except IOError:
                        self.log.warning(f"Failed to read file {file_attr.filename} on {self.credentials.host}.")
                        continue

                    try:
                        for _ in callback(
                            data=data, source=f"{self.credentials.host}:{self.credentials.port}/{file_attr.filename}",
                        ):
                            pass  # callback is a generator object
                    except Exception as ex:
                        if settings.DEBUG:
                            raise
                        else:
                            self.log.error(
                                f"File source callback {callback} for file {file_attr.filename} on "
                                f"{self.credentials.host} failed: {ex}"
                            )
                    else:
                        self.archive(
                            file_attr.filename,
                            data,
                            delete_callback=partial(sftp.client.remove, file_attr.filename),
                            logger=self.log,
                        )

                        self._update_metrics(file_attr)
                else:
                    self.log.debug(f"{file_attr.filename} is a directory. Skipping")


class FileAgent(BaseAgent):
    def _do_import(self, data: bytes, source: str) -> t.Iterable[None]:
        self.log.info(f"Importing {source}")

        transactions_data = []
        for transaction in self.yield_transactions_data(data):
            transactions_data.append(transaction)
            yield

        # TODO: this is less than ideal, should be keep a session open?
        with db.session_scope() as session:
            yield from self._import_transactions(transactions_data, session=session, source=source)

    def yield_transactions_data(self, data: bytes) -> t.Iterable[dict]:
        raise NotImplementedError

    @cached_property
    def filesource(self) -> FileSourceBase:
        filesource_class: t.Type[FileSourceBase] = (BlobFileSource if settings.BLOB_STORAGE_DSN else LocalFileSource)
        path = self.Config.path  # type: ignore
        return filesource_class(Path(path), logger=self.log)

    def run(self) -> None:
        self.log.info(f"Watching {self.filesource.path} for files via {self.filesource.__class__.__name__}.")

        scheduler = CronScheduler(
            schedule_fn=lambda: self.Config.schedule,  # type: ignore
            callback=self.callback,
            coalesce_jobs=True,
            logger=self.log,
        )

        self.log.debug(f"Beginning {scheduler}.")
        scheduler.run()

    def callback(self):
        attempts = 0
        while True:
            if not tasks.import_queue.has_capacity():
                attempts += 1
                delay_seconds = retry.exponential_delay(attempts, 15 * 60)
                humanize_delta = humanize.naturaldelta(datetime.timedelta(seconds=delay_seconds))
                self.log.info(f"Import queue is at capacity. Suspending for {humanize_delta}.")
                time.sleep(delay_seconds)
                continue  # retry

            self.filesource.provide(self._do_import)
            break
