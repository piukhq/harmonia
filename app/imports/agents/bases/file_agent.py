from pathlib import Path
import typing as t
import logging
import shutil
import time

from azure.storage.blob import BlobServiceClient
from azure.common import AzureConflictHttpError, AzureMissingResourceHttpError
import pendulum

from app.imports.agents import BaseAgent
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
        shutil.move(filepath, archive_path)

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
        self._bbs = BlobServiceClient.from_connection_string(settings.BLOB_CONNECTION_STRING)

    def archive(self, blob_name, blob_content, lease_id: str) -> None:
        archive_container = f"archive-{pendulum.today().to_date_string()}"
        self._bbs.create_container(container_name=archive_container)
        self._bbs.get_blob_client(archive_container, blob_name).upload_blob(blob_content)
        self._bbs.get_blob_client(self.container_name, blob_name).delete_blob(lease_id=lease_id)

    def provide(self, callback: t.Callable) -> None:
        self._bbs.create_container(container_name=self.container_name)
        container = self._bbs.get_container_client(self.container_name)
        for blob in container.list_blobs(name_starts_with=self.path):
            blob_client = self._bbs.get_blob_client(self.container_name, blob.name)
            try:
                lease_id = blob_client.acquire_lease(lease_duration=60)
            except AzureConflictHttpError:
                self.log.debug(f"Skipping blob {blob.name} as it is already leased.")
                continue
            except AzureMissingResourceHttpError:
                self.log.debug(f"Skipping blob {blob.name} as it has been deleted.")
                continue

            content = blob_client.download_blob(lease_id=lease_id).readall()

            self.log.debug(f"Invoking callback for blob {blob.name}.")

            try:
                callback(data=content, source=f"{self.container_name}/{blob.name}")
            except Exception as ex:
                if settings.DEBUG:
                    raise
                else:
                    self.log.error(f"File source callback {callback} for blob {blob.name} failed: {ex}.")
            else:
                self.archive(blob.name, content, lease_id)


class FileAgent(BaseAgent):
    def _do_import(self, data: bytes, source: str) -> None:
        self.log.info(f"Importing {source}")
        transactions_data = list(self.yield_transactions_data(data))
        self._import_transactions(transactions_data, source=source)

    def yield_transactions_data(self, data: bytes) -> t.Iterable[dict]:
        raise NotImplementedError

    def run(self, *, once: bool = False) -> None:
        filesource_class: t.Type[FileSourceBase] = (BlobFileSource if settings.USE_BLOB_STORAGE else LocalFileSource)
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
