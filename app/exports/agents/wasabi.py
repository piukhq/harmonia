import hashlib
import typing as t

import pendulum

from app import db, models
from app.config import KEY_PREFIX, ConfigValue
from app.encryption import decrypt_credentials
from app.exports.agents.bases.base import AgentExportData, AgentExportDataOutput
from app.exports.agents.bases.singular_export_agent import SingularExportAgent
from app.service.acteol import ActeolAPI
from app.service.atlas import atlas
from harness.exporters.acteol_mock import ActeolMockAPI
import settings

PROVIDER_SLUG = "wasabi-club"

BASE_URL_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.base_url"


class Wasabi(SingularExportAgent):
    provider_slug = PROVIDER_SLUG

    class ReceiptNumberNotFound(Exception):
        pass

    class Config:
        base_url = ConfigValue(BASE_URL_KEY, "http://localhost")

    def __init__(self):
        super().__init__()
        api_class = ActeolMockAPI if settings.DEVELOPMENT else ActeolAPI
        self.api = api_class(self.Config.base_url)

    def get_retry_datetime(self, retry_count: int) -> t.Optional[pendulum.DateTime]:
        if retry_count == 0:
            # first retry in 20 minutes.
            return pendulum.now("UTC") + pendulum.duration(minutes=20)
        elif retry_count == 1:
            # second retry at 3 AM the next day.
            return (pendulum.now("UTC") + pendulum.duration(days=1)).at(6)
        else:
            # after the previous two tries, give up.
            return None

    def make_export_data(self, matched_transaction: models.MatchedTransaction) -> AgentExportData:
        user_identity = matched_transaction.payment_transaction.user_identity
        credentials = decrypt_credentials(user_identity.credentials)
        return AgentExportData(
            outputs=[
                AgentExportDataOutput(
                    "export.json",
                    {
                        "origin_id": hashlib.sha1(f'Bink-Wasabi-{credentials["email"]}'.encode()).hexdigest(),
                        "ReceiptNo": matched_transaction.transaction_id,
                    },
                )
            ],
            transactions=[matched_transaction],
            extra_data={"credentials": credentials},
        )

    def export(self, export_data: AgentExportData, *, session: db.Session):
        _, body = export_data.outputs[0]
        request_timestamp = pendulum.now().to_datetime_string()
        response = self.api.post_matched_transaction(body)
        response_timestamp = pendulum.now().to_datetime_string()

        if msg := response.json().get("Message"):
            if msg.lower() == "receipt no not found":
                # fail the export for it to be retried later
                raise self.ReceiptNumberNotFound

            self.log.warn(f"Acteol API response contained message: {msg}")

        atlas.save_transaction(
            self.provider_slug, response, body, export_data.transactions, request_timestamp, response_timestamp
        )
