import settings

from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError

from app import reporting


log = reporting.get_logger("blob-storage")


class BlobStorageClient:
    def __init__(self):
        if settings.BLOB_STORAGE_DSN is not None:
            self.client = BlobServiceClient.from_connection_string(settings.BLOB_STORAGE_DSN)
        else:
            self.client = None

    def create_blob(self, container_name: str, blob_name: str, content: str):
        if self.client is None:
            log.warning(f'Blob storage is not configured. Skipping creation of blob "{container_name}/{blob_name}".')
            return
        try:
            self.client.create_container(container_name)
        except ResourceExistsError:
            pass
        blob_client = self.client.get_blob_client(container_name, blob_name)
        blob_client.upload_blob(content, blob_type="BlockBlob")
