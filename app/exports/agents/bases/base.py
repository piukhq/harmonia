from app import models
from app.reporting import get_logger
from app.service.blob_storage import BlobStorageClient

import pendulum
import os


def _missing_property(obj, prop: str):
    raise NotImplementedError(f"{type(obj).__name__} is missing a required property: {prop}")


class BaseAgent:
    def __init__(self) -> None:
        self.log = get_logger(f"export-agent.{self.provider_slug}")

    @property
    def provider_slug(self) -> str:
        return _missing_property(self, "provider_slug")

    def __repr__(self) -> str:
        return f"{type(self).__name__}(provider_slug={self.provider_slug})"

    def __str__(self) -> str:
        return f"export agent {type(self).__name__} for {self.provider_slug}"

    def help(self) -> str:
        return (
            "This is a new export agent.\n"
            "Implement all the required methods (see agent base classes) "
            "and override this help method to provide specific information."
        )

    def run(self, *, once: bool = False):
        raise NotImplementedError("This method should be overridden by specialised base agents.")

    def make_export_data(self, matched_transaction_id: int):
        raise NotImplementedError(
            "Override the make export data method in your export agent"
        )

    def handle_pending_export(self, pending_export: models.PendingExport) -> None:
        raise NotImplementedError("This method should be overridden by specicialised base agents.")

    def export(self, export_data: dict):
        raise NotImplementedError(
            "Override the export method in your agent to act as the entry point into the singular export process."
        )

    def export_all(self):
        raise NotImplementedError(
            "Override the export_all method in your agent to act as the entry point into the batch export process."
        )

    def save_export_data_to_file(self, export_data: dict) -> None:

        slug = export_data["transaction"].merchant_identifier.loyalty_scheme.slug

        filename = f"export_data-{slug}-{pendulum.now().isoformat()}.json"
        file_path = os.path.join("files/tmp/", filename)

        export_file = open(file_path, "w+")
        export_file.write(str(export_data))
        export_file.close()

        blob_storage_client = BlobStorageClient()
        blob_storage_client.azure_write(file_path, filename)
