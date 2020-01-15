import json
import inspect
import requests
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

    def help(self):
        return inspect.cleandoc(
            f"""
            This agent exports {self.provider_slug} transactions on a schedule of {self.Config.schedule}
            """
        )

    @staticmethod
    def check_response(response):
        try:
            errors = response.json().get("error_codes")
            if errors:
                raise requests.RequestException("Error codes found in export response: {}".format(errors))

        except (AttributeError, json.JSONDecodeError):
            if not response.content:
                return

            raise requests.RequestException(
                "Received error response when posting transactions: {}".format(response.content)
            )

    def format_transactions(self, transactions):
        formatted = []
        for transaction in transactions:
            formatted_transaction = {
                "record_uid": hashids.encode(transaction.user_identity.scheme_account_id),
                "merchant_scheme_id1": hashids.encode(transaction.user_identity.scheme_account_id),
                "merchant_scheme_id2": transaction.merchant_identifier.mid,
                "transaction_id": transaction.transaction_id,
            }
            formatted.append(formatted_transaction)

        return formatted

    def format_request(self, request_data):
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

    def internal_requests(self, response, transactions, atlas_status):
        for transaction in transactions:
            self.save_data(transaction, response)
            atlas.status_request(self.provider_slug, response, transaction, atlas_status)

    def export_all(self, once=True):
        if settings.ATLAS_URL is None:
            raise settings.ConfigVarRequiredError("ATLAS_URL is required for Iceland exports.")

        if settings.VAULT_DSN is None or settings.VAULT_TOKEN:
            raise settings.ConfigVarRequiredError("Both VAULT_DSN and VAULT_TOKEN are required for Iceland exports.")

        transactions_query_set = session.query(models.MatchedTransaction).filter_by(
            status=models.MatchedTransactionStatus.PENDING
        )

        formatted_transactions = self.format_transactions(transactions_query_set)
        request_data = {"message_uid": str(uuid4()), "transactions": formatted_transactions}

        request = self.format_request(request_data)

        try:
            response = self.api.merchant_request(request)
            self.check_response(response)
            self.internal_requests(response.text, transactions_query_set, atlas.Status.BINK_ASSIGNED)
        except requests.exceptions.RequestException as error:
            self.internal_requests(repr(error), transactions_query_set, atlas.Status.NOT_ASSIGNED)
            self.log.error(f"Iceland export request failed with the following exception: {error}")
