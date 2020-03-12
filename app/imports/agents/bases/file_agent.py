from pathlib import Path
import typing as t
import logging
import shutil
import time

from azure.storage.blob import BlobServiceClient, BlobLeaseClient
from azure.core.exceptions import ResourceExistsError, HttpResponseError
import pendulum

from app.imports.agents import BaseAgent
from app import reporting
import settings


logging.getLogger("azure").setLevel(logging.CRITICAL)


class FileSourceBase:
    def __init__(self, path: Path, *, logger: logging.Logger) -> None:
        self.path = path
        self.log = logger

    def provide(self, callback: t.Callable) -> None:
        raise NotImplementedError(f"{type(self).__name__} does not implement provide()")


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
                callback(data=data, source=str(filepath))
            except Exception as ex:
                if settings.DEBUG:
                    raise
                else:
                    self.log.error(f"File source callback {callback} for file {filepath} failed: {ex}")
            else:
                self.archive(filepath)


class BlobFileSource(FileSourceBase):
    container_name = "imports"

    def __init__(self, path: Path, *, logger: logging.Logger) -> None:
        super().__init__(path, logger=logger)
        self.log = reporting.get_logger("blob-file-source")
        self._bbs = BlobServiceClient.from_connection_string(settings.BLOB_STORAGE_DSN)

    def archive(self, blob_name: str, blob_content: bytes, lease: BlobLeaseClient) -> None:
        archive_container = f"archive-{pendulum.today().to_date_string()}"
        try:
            self._bbs.create_container(archive_container)
        except ResourceExistsError:
            pass  # this is fine

        try:
            self._bbs.get_blob_client(archive_container, blob_name).upload_blob(blob_content)
        except ResourceExistsError:
            self.log.warning(f"Failed to archive {blob_name} as this blob already exists in the archive.")

        self._bbs.get_blob_client(self.container_name, blob_name).delete_blob(lease=lease)

    def provide(self, callback: t.Callable) -> None:
        try:
            self._bbs.create_container(self.container_name)
        except ResourceExistsError:
            pass  # this is fine

        container = self._bbs.get_container_client(self.container_name)
        for blob in container.list_blobs(name_starts_with=self.path):
            blob_client = self._bbs.get_blob_client(self.container_name, blob.name)

            try:
                lease = blob_client.acquire_lease(lease_duration=60)
            except HttpResponseError:
                self.log.debug(f"Skipping blob {blob.name} as we could not acquire a lease.")
                continue

            content = blob_client.download_blob(lease=lease).readall()

            self.log.debug(f"Invoking callback for blob {blob.name}.")

            try:
                callback(data=content, source=f"{self.container_name}/{blob.name}")
            except Exception as ex:
                if settings.DEBUG:
                    raise
                else:
                    self.log.error(f"File source callback {callback} for blob {blob.name} failed: {ex}.")
            else:
                self.archive(blob.name, content, lease)


class FileAgent(BaseAgent):
    def _do_import(self, data: bytes, source: str) -> None:
        self.log.info(f"Importing {source}")
        transactions_data = list(self.yield_transactions_data(data))
        self._import_transactions(transactions_data, source=source)

    def yield_transactions_data(self, data: bytes) -> t.Iterable[dict]:
        raise NotImplementedError

    def run(self, *, once: bool = False) -> None:
        filesource_class: t.Type[FileSourceBase] = (BlobFileSource if settings.BLOB_STORAGE_DSN else LocalFileSource)
        path = self.Config.path  # type: ignore
        filesource = filesource_class(Path(path), logger=self.log)

        self.log.info("Starting import loop.")

        while True:
            filesource.provide(self._do_import)
            if once is True:
                self.log.info("Quitting early as we were told to run once.")
                break
            time.sleep(30)

        self.log.info("Shutting down.")
