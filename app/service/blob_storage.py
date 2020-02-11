import os
import settings

from azure.storage.blob import BlobServiceClient


class BlobStorageClient:
    @staticmethod
    def create_file(container_name, folder_name, file_name, file_content):
        blob_service = BlobServiceClient.from_connection_string(settings.BLOB_STORAGE_DSN)

        file_path = os.path.join(folder_name, file_name)
        blob_client = blob_service.get_blob_client(container_name, file_path)
        blob_client.upload_blob(file_content, blob_type="BlockBlob")
