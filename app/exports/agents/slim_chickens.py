import base64
import json
from pathlib import Path
from urllib.parse import urljoin

import pendulum
from requests import Session

import settings
from app import db, models
from app.config import KEY_PREFIX, Config, ConfigValue
from app.core.requests_retry import requests_retry_session
from app.exports.agents.bases.base import AgentExportData, AgentExportDataOutput
from app.exports.agents.bases.singular_export_agent import SingularExportAgent
from app.prometheus import bink_prometheus
from app.reporting import get_logger
from app.service import atlas, slim_chickens

SLIM_CHICKENS_SECRET_KEY = "slim-chickens-tx-export-secrets"

PROVIDER_SLUG = "slim-chickens"

BASE_URL_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.base_url"
AUTH_URL_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.auth_url"
log = get_logger("slim-chickens")


def _read_secrets(key: str) -> str:
    try:
        path = Path(settings.SECRETS_PATH) / key
        print(path.resolve())
        with path.open() as f:
            return json.loads(f.read())
    except FileNotFoundError as e:
        log.exception(e)
        raise


class SlimChickens(SingularExportAgent):
    provider_slug = PROVIDER_SLUG
    config = Config(
        ConfigValue("base_url", key=BASE_URL_KEY, default="https://localhost"),
        ConfigValue("auth_url", key=AUTH_URL_KEY, default="https://localhost-auth"),
    )

    def __init__(self):
        super().__init__()
        self.secrets = _read_secrets(SLIM_CHICKENS_SECRET_KEY)
        self.session = requests_retry_session()
        self.bink_prometheus = bink_prometheus

    def get_auth_token(self, transaction: models.ExportTransaction, session: Session) -> str:
        username = transaction.decrypted_credentials["email"]
        password = transaction.decrypted_credentials["password"]
        auth_credentials = f"{username}-{self.secrets['channel_key']}:{password}"

        self.auth_header = base64.b64encode(auth_credentials.encode()).decode()
        headers = {"Authorization": f"Basic {self.auth_header}"}

        auth_url = self.config.get("auth_url", session)
        url = urljoin(auth_url, "search")

        body = {"channelKeys": [self.secrets["channel_key"]], "types": ["wallet"]}
        resp = self.session.post(url, json=body, headers=headers)
        wallet_data = resp.json()["wallet"]
        in_progress_voucher = next((voucher for voucher in wallet_data if "cardPoints" in voucher), None)
        if in_progress_voucher:
            return in_progress_voucher["voucherCode"]
        return ""

    def make_export_data(self, export_transaction: models.ExportTransaction, session: db.Session) -> AgentExportData:

        return AgentExportData(
            outputs=[
                AgentExportDataOutput(
                    "export.json",
                    {
                        "token": self.get_auth_token(export_transaction, session),
                        "location": {
                            "incomingIdentifier": export_transaction.location_id,
                            "parentIncomingIdentifier": "slimchickens",
                        },
                    },
                )
            ],
            transactions=[export_transaction],
            extra_data=export_transaction.extra_fields,
        )

    def export(self, export_data: AgentExportData, *, retry_count: int = 0, session: db.Session) -> None:
        body: dict
        _, body = export_data.outputs[0]  # type: ignore
        api = slim_chickens.SlimChickensApi(
            self.config.get("base_url", session),
            self.secrets["client_secret"],
            self.secrets["client_id"],
            self.auth_header,
        )
        endpoint = "connect/account/redeem"
        request_timestamp = pendulum.now().to_datetime_string()
        response = api.post_matched_transaction(body, endpoint)
        response_timestamp = pendulum.now().to_datetime_string()

        request_url = urljoin(api.base_url, endpoint)
        atlas.queue_audit_message(
            atlas.make_audit_message(
                self.provider_slug,
                atlas.make_audit_transactions(
                    export_data.transactions, tx_loyalty_ident_callback=lambda tx: tx.loyalty_id
                ),
                request=body,
                request_timestamp=request_timestamp,
                response=response,
                response_timestamp=response_timestamp,
                request_url=request_url,
                retry_count=retry_count,
            )
        )
