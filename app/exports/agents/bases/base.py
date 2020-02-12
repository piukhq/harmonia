from app import models
from app.reporting import get_logger
from app.service.blob_storage import BlobStorageClient
from app.models import MatchedTransaction
from dataclasses import dataclass

import typing as t
import pendulum
import json


@dataclass
class AgentExportData:
    body: dict
    transactions: t.List[MatchedTransaction]


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

    def _save_to_file(self, export_data: AgentExportData) -> None:
        provider_slug = export_data.transactions[0].merchant_identifier.loyalty_scheme.slug
        file_name = f"{provider_slug}-export_data-{pendulum.now().isoformat()}.json"
        file_content = json.dumps(export_data.body)

        blob_storage_client = BlobStorageClient()
        blob_storage_client.create_file("exports", provider_slug, file_name, file_content)
