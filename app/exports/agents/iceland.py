import inspect
import json
import typing as t
from uuid import uuid4

import requests
from hashids import Hashids
from soteria.configuration import Configuration
from soteria.security import get_security_agent

import settings
from app import models, db
from app.config import KEY_PREFIX, ConfigValue
from app.exports.agents import AgentExportData, AgentExportDataOutput, BatchExportAgent
from app.service.atlas import atlas
from app.service.iceland import IcelandAPI

PROVIDER_SLUG = "iceland-bonus-card"
SCHEDULE_KEY = f"{KEY_PREFIX}agents.exports.{PROVIDER_SLUG}.schedule"

hash_ids = Hashids(
    min_length=32, salt="GJgCh--VgsonCWacO5-MxAuMS9hcPeGGxj5tGsT40FM", alphabet="abcdefghijklmnopqrstuvwxyz1234567890"
)


class Iceland(BatchExportAgent):
    provider_slug = PROVIDER_SLUG

    class Config:
        schedule = ConfigValue(SCHEDULE_KEY, "* * * * *")

    def __init__(self):
        super().__init__()

        if settings.ATLAS_URL is None:
            raise settings.ConfigVarRequiredError(
                f"The {self.provider_slug} export agent requires the Atlas URL to be set."
            )

        if settings.EUROPA_URL is None:
            raise settings.ConfigVarRequiredError(
                f"The {self.provider_slug} export agent requires the Europa URL to be set."
            )

        if settings.VAULT_URL is None or settings.VAULT_TOKEN is None:
            raise settings.ConfigVarRequiredError(
                f"The {self.provider_slug} export agent requires both the Vault URL and token to be set."
            )

        self.merchant_config = Configuration(
            self.provider_slug,
            Configuration.TRANSACTION_MATCHING_HANDLER,
            settings.VAULT_URL,
            settings.VAULT_TOKEN,
            settings.EUROPA_URL,
        )

    def help(self) -> str:
        return inspect.cleandoc(
            f"""
            This agent exports {self.provider_slug} transactions on a schedule of {self.Config.schedule}
            """
        )

    @staticmethod
    def check_response(response: requests.Response):
        try:
            errors = response.json().get("error_codes")
            if errors:
                raise requests.RequestException(f"Error codes found in export response: {errors}")
        except (AttributeError, json.JSONDecodeError):
            if not response.content:
                return

            raise requests.RequestException(f"Received error response when posting transactions: {response.text}")

    def format_transactions(self, transactions: t.Iterable[models.MatchedTransaction]) -> t.List[dict]:
        formatted = []
        for transaction in transactions:
            user_identity: models.UserIdentity = transaction.payment_transaction.user_identity
            formatted_transaction = {
                "record_uid": hash_ids.encode(user_identity.scheme_account_id),
                "merchant_scheme_id1": hash_ids.encode(user_identity.user_id),
                "merchant_scheme_id2": transaction.merchant_identifier.mid,
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

    def save_to_atlas(self, response: str, transaction: models.MatchedTransaction, status: atlas.Status):
        atlas.save_transaction(self.provider_slug, response, transaction, status)

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
        _, body = export_data.outputs.pop()
        request = self.make_secured_request(t.cast(str, body))

        api = IcelandAPI(self.merchant_config.merchant_url)

        try:
            response = api.merchant_request(request)
            self.check_response(response)
        except requests.exceptions.RequestException as error:
            response_text = repr(error)
            atlas_status = atlas.Status.NOT_ASSIGNED
            self.log.error(f"Iceland export request failed with the following exception: {error}")
        else:
            response_text = response.text
            atlas_status = atlas.Status.BINK_ASSIGNED

        for transaction in export_data.transactions:
            self.save_to_atlas(response_text, transaction, atlas_status)
