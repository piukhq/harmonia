import datetime
import json
import os
import typing as t
from uuid import uuid4

from soteria.security import get_security_agent

from app import db, models
from app.config import KEY_PREFIX, Config, ConfigValue
from app.encryption import decrypt_credentials
from app.exports.agents import AgentExportData, AgentExportDataOutput, BatchExportAgent
from app.sequences import batch
from app.service.cooperative import CooperativeAPI
from app.soteria import SoteriaConfigMixin

PROVIDER_SLUG = "cooperative"
SCHEDULE_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.schedule"
MAX_TRANSACTIONS_PER_REQUEST_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.max_transactions_per_request"


class Cooperative(BatchExportAgent, SoteriaConfigMixin):
    provider_slug = PROVIDER_SLUG

    config = Config(
        ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *"),
        ConfigValue("max_transactions_per_request", key=MAX_TRANSACTIONS_PER_REQUEST_KEY, default="10000"),
    )

    def __init__(self):
        super().__init__()

        self.soteria_config = self.get_soteria_config()
        self.api = CooperativeAPI(self.soteria_config.merchant_url)

    @staticmethod
    def save_backup_file(response):
        if response.json():
            filename = f"archive-coop-resp-{str(datetime.datetime.now().timestamp())}.json"
            path = os.path.join("files/backup/", filename)

            backup_file = open(path, "w+")
            backup_file.write(json.dumps(response.json()))
            backup_file.close()

    def serialize_transactions(self, matched_transactions):
        result = []
        for transaction in matched_transactions:
            credentials = decrypt_credentials(transaction.payment_transaction.user_identity.credentials)
            result.append(
                {
                    "record_uid": str(uuid4()),
                    "member_id": transaction.merchant_identifier_id,
                    "card_number": credentials["card_number"],
                    "transaction_id": transaction.transaction_id,
                }
            )
        return result

    def _refresh_auth_token(self, json_data, security_service, security_credentials, scope):
        security_credentials["outbound"]["credentials"][0]["value"]["payload"]["scope"] = scope
        outbound_security_agent = get_security_agent(security_service, security_credentials)

        auth_token_request = outbound_security_agent.encode(json_data)
        token = auth_token_request["headers"]["Authorization"].split()[1]

        return token

    def get_security_headers(self, body, *, security_service, security_credentials):
        access_token = self._refresh_auth_token(
            json.dumps(body), security_service, security_credentials, "bink-api/matched-transactions"
        )

        return {
            "Authorization": (
                f'{security_credentials["outbound"]["credentials"][0]["value"]["prefix"]} {access_token}'
            ),
            "X-API-KEY": security_credentials["outbound"]["credentials"][0]["value"]["api_key"],
        }

    def yield_export_data(
        self, transactions: t.List[models.MatchedTransaction], *, session: db.Session
    ) -> t.Iterable[AgentExportData]:
        self.log.debug(f"Starting {self.provider_slug} batch export loop.")
        batch_size = int(self.config.get("max_transactions_per_request", session=session))
        for transaction_batch in batch(transactions, batch_size):
            self.log.debug(f"Found a batch of {len(transaction_batch)} transactions to export.")
            transactions = self.serialize_transactions(transaction_batch)
            yield AgentExportData(
                outputs=[
                    AgentExportDataOutput("export.json", {"message_uid": str(uuid4()), "transactions": transactions})
                ],
                transactions=transaction_batch,
                extra_data={},
            )

    def send_export_data(self, export_data: AgentExportData, session: db.Session):
        self.log.debug(f"Starting {self.provider_slug} batch export loop.")
        _, body = export_data.outputs[0]
        # matched_transactions = export_data.transactions

        headers = self.get_security_headers(
            body,
            security_service=self.soteria_config.data["security_credentials"]["outbound"]["service"],
            security_credentials=self.soteria_config.data["security_credentials"],
        )

        response = self.api.export_transactions(body, headers)
        response.raise_for_status()

        self.save_backup_file(response)
        # self.send_to_atlas(response, matched_transactions)
