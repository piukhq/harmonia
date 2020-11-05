import json
import typing as t
from dataclasses import dataclass

import pendulum
import settings
from app import db, models
from app.models import MatchedTransaction
from app.reporting import get_logger
from app.service.blob_storage import BlobStorageClient
from app.utils import missing_property


class AgentExportDataOutput(t.NamedTuple):
    key: str
    data: t.Union[str, t.Dict, t.List]


@dataclass
class AgentExportData:
    outputs: t.List[AgentExportDataOutput]
    transactions: t.List[MatchedTransaction]
    extra_data: dict


class BaseAgent:
    # Can be overridden by child classes to set which output should be saved into the export_transaction table.
    saved_output_index = 0

    def __init__(self) -> None:
        self.log = get_logger(f"export-agent.{self.provider_slug}")

    @property
    def provider_slug(self) -> str:
        return missing_property(type(self), "provider_slug")

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

    def run(self):
        raise NotImplementedError("This method should be overridden by specialised base agents.")

    def handle_pending_export(self, pending_export: models.PendingExport, *, session: db.Session) -> None:
        raise NotImplementedError("This method should be overridden by specialised base agents.")

    def export(self, export_data: AgentExportData, *, session: db.Session):
        raise NotImplementedError(
            "Override the export method in your agent to act as the entry point into the singular export process."
        )

    def export_all(self, *, session: db.Session):
        raise NotImplementedError(
            "Override the export_all method in your agent to act as the entry point into the batch export process."
        )

    def _save_to_blob(self, export_data: AgentExportData):
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
            blob_storage_client.create_blob(settings.BLOB_EXPORT_CONTAINER, blob_name, content)

    def _save_export_transactions(self, export_data: AgentExportData, *, session: db.Session):
        self.log.info(f"Saving {len(export_data.transactions)} {self.provider_slug} export transactions to database.")
        self.log.debug(f"Data field comes from index #{self.saved_output_index} of {export_data.outputs}")

        def add_transactions():
            session.bulk_save_objects(
                models.ExportTransaction(
                    matched_transaction_id=transaction.id,
                    transaction_id=transaction.transaction_id,
                    provider_slug=self.provider_slug,
                    destination=export_data.outputs[self.saved_output_index].key,
                    data=export_data.outputs[self.saved_output_index].data,
                )
                for transaction in export_data.transactions
            )

            for transaction in export_data.transactions:
                transaction.status = models.MatchedTransactionStatus.EXPORTED

            session.commit()

        db.run_query(add_transactions, session=session, description="save export transactions")

    def _update_metrics(self, export_data: AgentExportData, session: t.Optional[db.Session]) -> None:
        """
        Update (optional) Prometheus metrics
        """
        raise NotImplementedError("This method should be overridden by specialised base agents.")
