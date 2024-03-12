import typing as t

from app import db, models
from app.exports.agents import AgentExportData, BatchExportAgent
from app.service import atlas
from app.soteria import SoteriaConfigMixin

PROVIDER_SLUG = "stonegate-unmatched"


class StonegateUnmatched(BatchExportAgent, SoteriaConfigMixin):
    provider_slug = PROVIDER_SLUG

    def __init__(self):
        super().__init__()

        self.merchant_config = self.get_soteria_config()

        # Set up Prometheus metric types
        self.prometheus_metrics = {
            "counters": ["requests_sent", "failed_requests", "transactions"],
            "histograms": ["request_latency"],
        }

    def yield_export_data(
        self, transactions: t.List[models.MatchedTransaction], *, session: db.Session
    ) -> t.Iterable[AgentExportData]:
        pass

    def send_export_data(self, export_data: AgentExportData, *, session: db.Session) -> atlas.MessagePayload:
        pass
