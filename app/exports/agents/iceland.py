import inspect
import json
import typing as t
import settings
import pendulum

from uuid import uuid4
from hashids import Hashids
from soteria.security import get_security_agent

from app import models, db
from app.config import KEY_PREFIX, Config, ConfigValue
from app.exports.agents import AgentExportData, AgentExportDataOutput, BatchExportAgent
from app.service import atlas
from app.service.iceland import IcelandAPI
from app.soteria import SoteriaConfigMixin
from app.sequences import batch
from harness.exporters.iceland_mock import IcelandMockAPI

PROVIDER_SLUG = "iceland-bonus-card"
SCHEDULE_KEY = f"{KEY_PREFIX}agents.exports.{PROVIDER_SLUG}.schedule"
BATCH_SIZE_KEY = f"{KEY_PREFIX}agents.exports.{PROVIDER_SLUG}.batch_size"

hash_ids = Hashids(
    min_length=32, salt="GJgCh--VgsonCWacO5-MxAuMS9hcPeGGxj5tGsT40FM", alphabet="abcdefghijklmnopqrstuvwxyz1234567890",
)


class Iceland(BatchExportAgent, SoteriaConfigMixin):
    provider_slug = PROVIDER_SLUG

    config = Config(
        ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *"),
        ConfigValue("batch_size", key=BATCH_SIZE_KEY, default="200"),
    )

    def __init__(self):
        super().__init__()

        if settings.ATLAS_URL is None:
            raise settings.ConfigVarRequiredError(
                f"The {self.provider_slug} export agent requires the Atlas URL to be set."
            )

        self.merchant_config = self.get_soteria_config()
        if settings.DEBUG is True:
            # Use mocked Iceland endpoints
            self.api = IcelandMockAPI(self.merchant_config.merchant_url)
        else:
            self.api = IcelandAPI(self.merchant_config.merchant_url)

        # Set up Prometheus metric types
        self.prometheus_metrics = {
            "counters": ["requests_sent", "failed_requests", "transactions"],
            "histograms": ["request_latency"],
        }

    def help(self, session: db.Session) -> str:
        return inspect.cleandoc(
            f"""
            This agent exports {self.provider_slug} transactions on a schedule of {self.config.get(
                "schedule", session=session
                )}
            """
        )

    @staticmethod
    def get_loyalty_identifier(matched_transaction: models.MatchedTransaction) -> str:
        return matched_transaction.payment_transaction.user_identity.decrypted_credentials["merchant_identifier"]

    @staticmethod
    def get_record_uid(matched_transaction: models.MatchedTransaction) -> str:
        return hash_ids.encode(matched_transaction.payment_transaction.user_identity.scheme_account_id)

    def format_transactions(self, transactions: t.Iterable[models.MatchedTransaction]) -> t.List[dict]:
        formatted = []
        for transaction in transactions:
            user_identity: models.UserIdentity = transaction.payment_transaction.user_identity
            formatted_transaction = {
                "record_uid": self.get_record_uid(transaction),
                "merchant_scheme_id1": hash_ids.encode(user_identity.user_id),
                "merchant_scheme_id2": self.get_loyalty_identifier(transaction),
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

    def _make_export_data(self, transactions: t.List[models.MatchedTransaction], *, index: int) -> AgentExportData:
        formatted_transactions = self.format_transactions(transactions)
        return AgentExportData(
            outputs=[
                AgentExportDataOutput(
                    f"export-{index + 1:03}.json",
                    json.dumps({"message_uid": str(uuid4()), "transactions": formatted_transactions}),
                )
            ],
            transactions=transactions,
            extra_data={},
        )

    def yield_export_data(
        self, transactions: t.List[models.MatchedTransaction], *, session: db.Session
    ) -> t.Iterable[AgentExportData]:
        batch_size = int(self.config.get("batch_size", session=session))
        for i, transaction_set in enumerate(batch(transactions, size=batch_size)):
            yield self._make_export_data(transaction_set, index=i)

    def send_export_data(self, export_data: AgentExportData, session: db.Session) -> atlas.MessagePayload:
        _, body = export_data.outputs[0]
        request = self.make_secured_request(t.cast(str, body))
        request_timestamp = pendulum.now().to_datetime_string()
        response = self.api.merchant_request(request)
        response_timestamp = pendulum.now().to_datetime_string()

        audit_message = atlas.make_audit_message(
            self.provider_slug,
            atlas.make_audit_transactions(
                export_data.transactions,
                tx_loyalty_ident_callback=self.get_loyalty_identifier,
                tx_record_uid_callback=self.get_record_uid,
            ),
            request=body,
            request_timestamp=request_timestamp,
            response=response,
            response_timestamp=response_timestamp,
        )
        return audit_message
