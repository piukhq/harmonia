import json
import inspect
import requests
import typing as t
from uuid import uuid4

from hashids import Hashids
from soteria.configuration import Configuration
from soteria.security import get_security_agent

from app import models
from app.db import session
from app.service.atlas import atlas
from app.config import ConfigValue, KEY_PREFIX
from app.exports.agents import BatchExportAgent
from app.service.iceland import IcelandAPI
import settings


PROVIDER_SLUG = "iceland-bonus-card"
SCHEDULE_KEY = f"{KEY_PREFIX}agents.exports.{PROVIDER_SLUG}.schedule"

hashids = Hashids(
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

        if settings.SOTERIA_URL is None:
            raise settings.ConfigVarRequiredError(
                f"The {self.provider_slug} export agent requires the Soteria URL to be set."
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
            settings.SOTERIA_URL,
        )

        self.api = IcelandAPI(self.merchant_config.merchant_url)

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
                "record_uid": hashids.encode(user_identity.scheme_account_id),
                "merchant_scheme_id1": hashids.encode(user_identity.user_id),
                "merchant_scheme_id2": transaction.merchant_identifier.mid,
                "transaction_id": transaction.transaction_id,
            }
            formatted.append(formatted_transaction)

        return formatted

    def make_secured_request(self, request_data: dict) -> dict:
        security_class = get_security_agent(
            self.merchant_config.data["security_credentials"]["outbound"]["service"],
            self.merchant_config.data["security_credentials"],
        )
        json_data = json.dumps(request_data)
        request = security_class.encode(json_data)

        return request

    def save_data(self, matched_transaction, export_data):
        session.add(
            models.ExportTransaction(
                matched_transaction_id=matched_transaction.id,
                transaction_id=matched_transaction.transaction_id,
                provider_slug=self.provider_slug,
                destination="",
                data=export_data,
            )
        )
        matched_transaction.status = models.MatchedTransactionStatus.EXPORTED
        session.commit()
        self.log.debug(f"The status of the transaction has been changed to: {matched_transaction.status}")

    def save_to_atlas(self, response: dict, transaction: models.MatchedTransaction, status: atlas.Status):
        atlas.save_transaction(self.provider_slug, response, transaction, status)

    def export_all(self, once=True):
        transactions_query_set = (
            session.query(models.MatchedTransaction)
            .filter(models.MatchedTransaction.status == models.MatchedTransactionStatus.PENDING)
            .all()
        )

        formatted_transactions = self.format_transactions(transactions_query_set)
        request_data = {"message_uid": str(uuid4()), "transactions": formatted_transactions}

        request = self.make_secured_request(request_data)

        try:
            response = self.api.merchant_request(request)
            self.check_response(response)
        except requests.exceptions.RequestException as error:
            response_text = repr(error)
            atlas_status = atlas.Status.NOT_ASSIGNED
            self.log.error(f"Iceland export request failed with the following exception: {error}")
        else:
            response_text = response.text
            atlas_status = atlas.Status.BINK_ASSIGNED

        for transaction in transactions_query_set:
            self.save_data(transaction, request)
            self.save_to_atlas(response_text, transaction, atlas_status)
