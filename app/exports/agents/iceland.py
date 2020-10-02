import inspect
import json
import typing as t
from uuid import uuid4

import pendulum
import settings
from app import db, models
from app.config import KEY_PREFIX, ConfigValue
from app.encryption import decrypt_credentials
from app.exports.agents import AgentExportData, AgentExportDataOutput, BatchExportAgent
from app.prometheus import prometheus_registry
from app.reporting import get_logger
from app.service.atlas import atlas
from app.service.iceland import IcelandAPI
from app.soteria import SoteriaConfigMixin
from harness.exporters.iceland_mock import IcelandMockAPI
from hashids import Hashids
from soteria.security import get_security_agent

PROVIDER_SLUG = "iceland-bonus-card"
SCHEDULE_KEY = f"{KEY_PREFIX}agents.exports.{PROVIDER_SLUG}.schedule"

hash_ids = Hashids(
    min_length=32, salt="GJgCh--VgsonCWacO5-MxAuMS9hcPeGGxj5tGsT40FM", alphabet="abcdefghijklmnopqrstuvwxyz1234567890"
)


logger = get_logger(__name__)

class Iceland(BatchExportAgent, SoteriaConfigMixin):
    provider_slug = PROVIDER_SLUG

    class Config:
        schedule = ConfigValue(SCHEDULE_KEY, "* * * * *")

    def __init__(self):
        super().__init__()
        self.request_latency_histogram = (
            prometheus_registry["export"]["single"][self.provider_slug]["histogram"]["request_latency"]
        )
        self.failed_requests_counter = (
            prometheus_registry["export"]["single"][self.provider_slug]["counter"]["failed_requests"]
        )
        self.transactions_counter = (
            prometheus_registry["export"]["single"][self.provider_slug]["counter"]["transactions"]
        )

        if settings.ATLAS_URL is None:
            raise settings.ConfigVarRequiredError(
                f"The {self.provider_slug} export agent requires the Atlas URL to be set."
            )

        self.merchant_config = self.get_soteria_config()
        if settings.DEVELOPMENT is True:
            # Use mocked Iceland endpoints
            self.api = IcelandMockAPI(self.merchant_config.merchant_url)
        else:
            self.api = IcelandAPI(self.merchant_config.merchant_url)

    def help(self) -> str:
        return inspect.cleandoc(
            f"""
            This agent exports {self.provider_slug} transactions on a schedule of {self.Config.schedule}
            """
        )

    def format_transactions(self, transactions: t.Iterable[models.MatchedTransaction]) -> t.List[dict]:
        formatted = []
        for transaction in transactions:
            user_identity: models.UserIdentity = transaction.payment_transaction.user_identity
            credential_values = decrypt_credentials(user_identity.credentials)
            formatted_transaction = {
                "record_uid": hash_ids.encode(user_identity.scheme_account_id),
                "merchant_scheme_id1": hash_ids.encode(user_identity.user_id),
                "merchant_scheme_id2": credential_values["merchant_identifier"],
                "transaction_id": transaction.transaction_id,
            }
            formatted.append(formatted_transaction)

        return formatted

    def make_secured_request(self, body: str) -> dict:
        security_class = get_security_agent(
            self.merchant_config.data["security_credentials"]["outbound"]["service"],
            self.merchant_config.data["security_credentials"],
        )
        return security_class.encode(body)

    def yield_export_data(
        self, transactions: t.List[models.MatchedTransaction], *, session: db.Session
    ) -> t.Iterable[AgentExportData]:
        formatted_transactions = self.format_transactions(transactions)

        yield AgentExportData(
            outputs=[
                AgentExportDataOutput(
                    "export.json", json.dumps({"message_uid": str(uuid4()), "transactions": formatted_transactions})
                )
            ],
            transactions=transactions,
            extra_data={},
        )

    def send_export_data(self, export_data: AgentExportData):
        _, body = export_data.outputs[0]
        request = self.make_secured_request(t.cast(str, body))
        request_timestamp = pendulum.now().to_datetime_string()
        response = self.api.merchant_request(request)
        response_timestamp = pendulum.now().to_datetime_string()

        atlas.save_transaction(
            self.provider_slug, response, request, export_data.transactions, request_timestamp, response_timestamp
        )
