import typing as t
import logging
import time
import io

from azure.storage.blob import Blob, BlockBlobService
from azure.common import AzureConflictHttpError

from app.imports.agents.bases.base import BaseAgent
import settings


logging.getLogger("azure").setLevel(logging.WARNING)


class BlobStorageAgent(BaseAgent):
    def __init__(self, *, debug: bool = False) -> None:
        super().__init__(debug=debug)
        self._bbs = BlockBlobService(account_name=settings.BLOB_ACCOUNT_NAME, account_key=settings.BLOB_ACCOUNT_KEY)

        self._bbs.create_container(container_name=settings.BLOB_CONTAINER_NAME)

    def _choose_importable_blob(self) -> t.Tuple[Blob, str]:
        """
        Returns an importable blob and its associated lease ID.
        """
        while True:
            blobs: t.List[Blob] = self._bbs.list_blobs(
                container_name=settings.BLOB_CONTAINER_NAME, prefix=self.Config.blob_prefix  # type: ignore
            )
            for blob in blobs:
                # attempt to lease the blob
                try:
                    lease_id = self._bbs.acquire_blob_lease(
                        container_name=settings.BLOB_CONTAINER_NAME,
                        blob_name=blob.name,
                        lease_duration=int(self.Config.blob_lease_duration),  # type: ignore
                    )
                except AzureConflictHttpError:
                    self.log.debug(f"Blob {blob.name} is already leased. Skipping.")
                    continue

                self.log.debug(f"Leased blob {blob.name} ({lease_id})")
                return blob, lease_id
            self.log.debug("No importable blobs. Waiting for 30 seconds.")
            time.sleep(30)

    def _importable_blobs(self) -> t.Iterable[t.Tuple[Blob, str]]:
        if self.once:
            yield self._choose_importable_blob()
            self.log.info("Quitting early as we were told to run once.")
            return

        while True:
            yield self._choose_importable_blob()

    def _import_blob(self, blob: Blob, lease_id: str) -> None:
        self.log.debug(f"Downloading blob {blob.name}…")
        fd = io.BytesIO()
        self._bbs.get_blob_to_stream(
            container_name=settings.BLOB_CONTAINER_NAME, blob_name=blob.name, stream=fd, lease_id=lease_id
        )
        self.log.debug(f"Download of blob {blob.name} complete. Importing…")
        self._do_import(fd, blob=blob, lease_id=lease_id)
        self.log.debug(f"Imported blob {blob.name} successfully.")

    def _do_import(self, fd: t.IO, *, blob: Blob, lease_id: str) -> None:
        transactions_data = list(self.yield_transactions_data(fd))  # type: ignore
        self._import_transactions(transactions_data, source=f"{settings.BLOB_CONTAINER_NAME}:{blob.name}")
        self.log.warning(
            f"We should move blob {blob.name} to an archive here, but instead we're just going to delete it."
        )
        self._bbs.delete_blob(container_name=settings.BLOB_CONTAINER_NAME, blob_name=blob.name, lease_id=lease_id)

    def run(self, *, once: bool = False) -> None:
        self.once = once

        self.log.info("Starting import loop.")
        for blob, lease_id in self._importable_blobs():
            self._import_blob(blob, lease_id)

        self.log.info("Shutting down.")
