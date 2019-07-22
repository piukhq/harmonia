from pathlib import Path
import typing as t
import logging
import shutil
import time

from azure.storage.blob import Blob, BlockBlobService
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
        self._bbs = BlockBlobService(settings.BLOB_ACCOUNT_NAME, settings.BLOB_ACCOUNT_KEY)

    def archive(self, blob: Blob, lease_id: str) -> None:
        archive_container = f"archive-{pendulum.today().to_date_string()}"
        self._bbs.create_container(container_name=archive_container)
        self._bbs.create_blob_from_bytes(container_name=archive_container, blob_name=blob.name, blob=blob.content)
        self._bbs.delete_blob(container_name=self.container_name, blob_name=blob.name, lease_id=lease_id)

    def provide(self, callback: t.Callable) -> None:
        self._bbs.create_container(container_name=self.container_name)
        for blob in self._bbs.list_blobs(container_name=self.container_name, prefix=self.path):
            try:
                lease_id = self._bbs.acquire_blob_lease(
                    container_name=self.container_name, blob_name=blob.name, lease_duration=60
                )
            except AzureConflictHttpError:
                self.log.debug(f"Skipping blob {blob.name} as it is already leased.")
                continue
            except AzureMissingResourceHttpError:
                self.log.debug(f"Skipping blob {blob.name} as it has been deleted.")
                continue

            # update blob with content
            blob = self._bbs.get_blob_to_bytes(
                container_name=self.container_name, blob_name=blob.name, lease_id=lease_id
            )

            self.log.debug(f"Invoking callback for blob {blob.name}.")

            try:
                callback(data=blob.content, source=f"{self.container_name}/{blob.name}")
            except Exception as ex:
                if settings.DEBUG:
                    raise
                else:
                    self.log.error(f"File source callback {callback} for blob {blob.name} failed: {ex}.")
            else:
                self.archive(blob, lease_id)


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
