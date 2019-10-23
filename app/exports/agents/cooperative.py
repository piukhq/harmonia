import os
import json
import inspect
import settings
import requests
import datetime

from uuid import uuid1
from app import models
from app.db import session
from app.service.atlas import atlas
from app.encryption import AESCipher
from app.config import ConfigValue, KEY_PREFIX
from soteria.security import get_security_agent
from app.exports.agents import BatchExportAgent
from app.service.cooperative import cooperative, config
from voluptuous import Schema, Any, Extra, Required, MultipleInvalid


SCHEDULE_KEY = f"{KEY_PREFIX}{settings.COOP_SCHEDULE_KEY}"


class Cooperative(BatchExportAgent):
    provider_slug = "cooperative"

    class Config:
        schedule = ConfigValue(SCHEDULE_KEY, "* * * * *")

    def help(self):
        return inspect.cleandoc(
            f"""
                This agent exports {self.provider_slug} transactions on a schedule of {self.Config.schedule}
                """
        )

    @staticmethod
    def decrypt_credentials(credentials):
        aes = AESCipher(settings.AES_KEY.encode())

        return json.loads(aes.decrypt(credentials.replace(" ", "+")))

    @staticmethod
    def check_response(response):
        content = response.json()
        cooperative_export = Schema(
            Any(
                [
                    Any(
                        {Required("processed"): str},
                        {Required("unfound"): str},
                        {Required("alreadyProcessed"): str},
                        {Extra: object},
                    )
                ],
                {"error_codes": list},
            )
        )

        try:
            cooperative_export(content)

            if type(content) == dict:
                raise requests.RequestException(
                    f"Received error response when posting transactions: {content['status']}"
                )
        except MultipleInvalid:
            if not response.content:
                return
            raise requests.RequestException(f"Received error response when posting transactions: {response.content}")

        response.raise_for_status()

    @staticmethod
    def save_backup_file(response):
        if response.json():
            filename = f"archive-coop-resp-{str(datetime.datetime.now().timestamp())}.json"
            path = os.path.join(settings.COOP_RESPONSE_BACKUP_PATH, filename)

            backup_file = open(path, "w+")
            backup_file.write(json.dumps(response.json()))
            backup_file.close()

    def build_json_data(self, transactions_query_set):
        formatted_transactions = []
        for transaction in transactions_query_set.limit(settings.COOP_LIMIT_PER_REQUEST):
            credentials = self.decrypt_credentials(transaction.user_identity.credentials)
            formatted_transaction = {
                "record_uid": str(uuid1()),
                "member_id": transaction.merchant_identifier_id,
                "card_number": credentials["card_number"],
                "transaction_id": transaction.transaction_id,
            }
            formatted_transactions.append(formatted_transaction)
        return {"message_uid": str(uuid1()), "transactions": formatted_transactions}

    def _refresh_auth_token(self, json_data, security_service, security_credentials, scope):
        security_credentials["outbound"]["credentials"][0]["value"]["payload"]["scope"] = scope
        outbound_security_agent = get_security_agent(security_service, security_credentials)

        auth_token_request = outbound_security_agent.encode(json_data)
        token = auth_token_request["headers"][settings.COOP_AUTH_TOKEN_HEADER].split()[1]

        return token

    def apply_security_measures(self, json_data, security_service, security_credentials):
        access_token = self._refresh_auth_token(
            json_data, security_service, security_credentials, settings.COOP_TRANSACTIONS_AUTH_SCOPE
        )

        return {
            "json": json.loads(json_data),
            "headers": {
                settings.COOP_AUTH_TOKEN_HEADER: "{} {}".format(
                    security_credentials["outbound"]["credentials"][0]["value"]["prefix"], access_token
                ),
                "X-API-KEY": security_credentials["outbound"]["credentials"][0]["value"]["api_key"],
            },
        }

    def build_request_data(self, json_data):
        return self.apply_security_measures(
            json.dumps(json_data),
            config.data["security_credentials"]["outbound"]["service"],
            config.data["security_credentials"],
        )

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

    def internal_requests(self, response, transactions_query):
        failed_transactions = []
        for transaction_response in response.json():
            transaction_status = str(list(transaction_response.keys())[0])
            transaction = transactions_query.filter_by(transaction_id=transaction_response[transaction_status]).one()
            if transaction_status.lower() in ["processed"]:
                self.save_data(transaction, transaction_response)
                try:
                    atlas.status_request(
                        self.provider_slug, transaction_response, transaction, atlas.Status.BINK_ASSIGNED
                    )
                except Exception:
                    failed_transactions.append(transaction)
                continue
            if transaction_status.lower() in ["alreadyprocessed", "alreadyclaimed", "alreadyassigned"]:
                self.save_data(transaction, transaction_response)
                try:
                    atlas.status_request(
                        self.provider_slug, transaction_response, transaction, atlas.Status.MERCHANT_ASSIGNED
                    )
                except Exception:
                    failed_transactions.append(transaction)
                continue
            if transaction_status.lower() in ["unfound"]:
                self.save_data(transaction, transaction_response)
                try:
                    atlas.status_request(
                        self.provider_slug, transaction_response, transaction, atlas.Status.NOT_ASSIGNED
                    )
                except Exception:
                    failed_transactions.append(transaction)
                continue
        if failed_transactions:
            self.log.error(f"Transactions {failed_transactions} has not been saved to the Atlas.")

    def export_all(self, once=True):
        transactions_query_set = session.query(models.MatchedTransaction).filter_by(
            status=models.MatchedTransactionStatus.PENDING
        )

        json_data = self.build_json_data(transactions_query_set)
        request_data = self.build_request_data(json_data)
        response = cooperative.merchant_request(request_data)
        self.check_response(response)
        self.save_backup_file(response)

        self.internal_requests(response, transactions_query_set)
