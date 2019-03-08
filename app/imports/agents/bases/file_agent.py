from pathlib import Path
import typing as t
import logging
import shutil
import time
import io

from azure.storage.blob import Blob, BlockBlobService
from azure.common import AzureConflictHttpError
import pendulum

from app.imports.agents.bases.base import BaseAgent
import settings


logging.getLogger("azure").setLevel(logging.WARNING)


class FileSourceBase:
    def __init__(self, path: Path) -> None:
        self.path = path

    def provide(self) -> t.Iterable[t.IO]:
        raise NotImplementedError(f"{type(self).__name__} does not implement provide()")


class LocalFileSource(FileSourceBase):
    def __init__(self, path: Path) -> None:
        path = settings.LOCAL_IMPORT_BASE_PATH / path
        super().__init__(path)

    def archive(self, filepath: Path) -> None:
        subpath = filepath.relative_to(self.path)
        archive_path = Path("archives") / pendulum.today().to_date_string() / subpath
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(filepath, archive_path)

    def provide(self) -> t.Iterable[t.IO]:
        for filepath in (p for p in self.path.iterdir() if p.is_file()):
            with open(filepath) as fd:
                yield fd
            self.archive(filepath)


class BlobFileSource(FileSourceBase):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self._bbs = BlockBlobService(settings.BLOB_ACCOUNT_NAME, settings.BLOB_ACCOUNT_KEY)

    def archive(self, blob: Blob, lease_id: str, fd: io.BytesIO) -> None:
        archive_container = f"archive-{pendulum.today().to_date_string()}"
        self._bbs.create_container(container_name=archive_container)
        self._bbs.create_blob_from_stream(container_name=archive_container, blob_name=blob.name, stream=fd)
        self._bbs.delete_blob(container_name=settings.BLOB_CONTAINER_NAME, blob_name=blob.name, lease_id=lease_id)

    def provide(self) -> t.Iterable[t.IO]:
        for blob in self._bbs.list_blobs(container_name=settings.BLOB_CONTAINER_NAME, prefix=self.path):
            try:
                lease_id = self._bbs.acquire_blob_lease(
                    container_name=settings.BLOB_CONTAINER_NAME, blob_name=blob.name, lease_duration=60
                )
            except AzureConflictHttpError:
                continue

            fd = io.BytesIO()
            fd.name = f"{settings.BLOB_CONTAINER_NAME}/{blob.name}"
            self._bbs.get_blob_to_stream(
                container_name=settings.BLOB_CONTAINER_NAME, blob_name=blob.name, stream=fd, lease_id=lease_id
            )

            fd.seek(0)
            yield fd

            fd.seek(0)
            self.archive(blob, lease_id, fd)

            fd.close()


class FileAgent(BaseAgent):
    def __init__(self, *, debug: bool = False) -> None:
        super().__init__(debug=debug)

    def _do_import(self, fd: t.IO) -> None:
        self.log.debug(f"Importing {fd.name}")
        transactions_data = list(self.yield_transactions_data(fd))  # type: ignore
        self._import_transactions(transactions_data, source=fd.name)

    def run(self, *, once: bool = False) -> None:
        filesource_class: t.Type[FileSourceBase] = (BlobFileSource if settings.USE_BLOB_STORAGE else LocalFileSource)
        filesource = filesource_class(Path(self.Config.path))  # type: ignore

        self.log.info("Starting import loop.")

        while True:
            for fd in filesource.provide():
                self._do_import(fd)

                if once:
                    self.log.info("Quitting early as we were told to run once.")
                    return

            self.log.debug("Waiting for 30 seconds.")
            time.sleep(30)

        self.log.info("Shutting down.")
