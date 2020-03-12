from app import models
from app.reporting import get_logger
from app.service.blob_storage import BlobStorageClient
from app.models import MatchedTransaction
from dataclasses import dataclass

import typing as t
import pendulum
import json


AgentExportDataOutput = t.Union[str, t.Dict, t.List]


@dataclass
class AgentExportData:
    outputs: t.List[t.Tuple[str, AgentExportDataOutput]]
    transactions: t.List[MatchedTransaction]
    extra_data: dict


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

    def export(self, export_data: AgentExportData):
        raise NotImplementedError(
            "Override the export method in your agent to act as the entry point into the singular export process."
        )

    def export_all(self):
        raise NotImplementedError(
            "Override the export_all method in your agent to act as the entry point into the batch export process."
        )

    def _save_to_blob(self, export_data: AgentExportData) -> None:
        self.log.info(
            f"Saving {self.provider_slug} export data to blob storage with {len(export_data.outputs)} outputs."
        )
        blob_name_prefix = f"{self.provider_slug}/export-{pendulum.now().isoformat()}/"
        blob_storage_client = BlobStorageClient()

        for name, output in export_data.outputs:
            if isinstance(output, str):
                content = output
            else:
                content = json.dumps(output)

            blob_name = f"{blob_name_prefix}{name}"
            blob_storage_client.create_blob("exports", blob_name, content)
