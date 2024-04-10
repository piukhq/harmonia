import json
from collections.abc import Callable
from decimal import Decimal

import settings
from app.reporting import get_logger
from app.service.atlas import AuditTransaction, make_audit_result, queue_audit_message
from app.utils import missing_property


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super().default(o)


class BaseAgent:
    def __init__(self) -> None:
        self.log = get_logger(f"export-result-agent.{self.provider_slug}")

    @property
    def provider_slug(self) -> str:
        return missing_property(type(self), "provider_slug")

    def run(self):
        raise NotImplementedError(
            "Override the run method in your agent to act as the main entry point into the export result process."
        )

    def _load_export_results(
        self,
        export_results: list[dict],
        export_transaction_callback: Callable[[dict], list[AuditTransaction]],
        *,
        source: str,
    ) -> int:
        for result in export_results:
            self._enqueue(result, export_transaction_callback(result), source)
        return len(export_results)

    def _enqueue(self, result: dict, export_transaction: list[AuditTransaction], source):
        if settings.AUDIT_EXPORTS:
            queue_audit_message(
                make_audit_result(
                    self.provider_slug,
                    export_transaction,
                    result=result,
                    result_timestamp=export_transaction[0]["event_date_time"],
                    source=source,
                )
            )
