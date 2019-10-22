#! /usr/bin/env python3
import os
import json
import requests
import settings

from app import models
from uuid import uuid4
from s import s_settings
from base64 import b64encode
from app.db import Base, session
from s.seed import get_or_create
from app.reporting import get_logger

HERMES_URL = settings.HERMES_URL
LOYALTY_SCHEME_SLUG = "cooperative"
PAYMENT_PROVIDER_SLUG = "bink-payment"
HARMONIA_URL = s_settings.HARMONIA_URL
COOP_FILE_WITH_TRANSACTIONS_PATH = s_settings.COOP_FILE_WITH_TRANSACTIONS_PATH
COOP_LIMIT_TRANSACTIONS_FROM_FILE = int(s_settings.COOP_LIMIT_TRANSACTIONS_FROM_FILE)

MOCK_TRANSACTIONS = {
    "transactions": [
        {
            "card": {"first_6": "465859", "last_4": "6029"},
            "amount": {"value": 5, "unit": "GBP"},
            "store_id": "7102932",
            "timestamp": "2019-06-29T10:53:00",
            "id": "7deec56b-9ba5-11e9-9b02-3d3e2f734b26-1",
        },
        {
            "card": {"first_6": "465902", "last_4": "4128"},
            "amount": {"value": 3, "unit": "GBP"},
            "store_id": "7102866",
            "timestamp": "2019-06-30T10:53:00",
            "id": "7deec56b-9ba5-11e9-9b02-3d3e2f734b26-2",
        },
    ]
}


def get(model: Base, query: list) -> Base:
    return session.query(model).filter(*query).one()


class CooperativeProducer(object):
    def __init__(self) -> None:
        self.log = get_logger(f"cooperative-processes")

    errors_in_processes = []

    loyalty_scheme = get(models.LoyaltyScheme, query=[models.LoyaltyScheme.slug == LOYALTY_SCHEME_SLUG])
    payment_provider = get(models.PaymentProvider, query=[models.PaymentProvider.slug == PAYMENT_PROVIDER_SLUG])

    def save_file(self, transactions, transactions_type):
        input_file_path = f"../harmonia/files/imports/cooperative/mock_transactions_{transactions_type}.dat"
        with open(input_file_path, "w") as f:
            json.dump(transactions, f)
        self.log.debug(f"Input file was created: {input_file_path}")

    def create_input_file(self):
        transactions = {}
        if os.path.isfile(COOP_FILE_WITH_TRANSACTIONS_PATH):
            with open(COOP_FILE_WITH_TRANSACTIONS_PATH, "r") as file:
                transactions["transactions"] = json.loads(file.read())["transactions"][
                    :COOP_LIMIT_TRANSACTIONS_FROM_FILE
                ]
                self.save_file(transactions, "from_file")
        else:
            self.save_file(MOCK_TRANSACTIONS, "mock_transactions")
            transactions = MOCK_TRANSACTIONS
        return transactions

    def add_all_mid(self, transactions):
        all_mids = []
        for transaction in transactions:
            try:
                all_mids.append(transaction["store_id"])
            except Exception as error:
                self.errors_in_processes.append(error)

        for mid in list(set(all_mids)):
            merchant_identifier, created = get_or_create(
                models.MerchantIdentifier,
                query=[models.MerchantIdentifier.mid == mid],
                create_fields={
                    "mid": mid,
                    "loyalty_scheme_id": self.loyalty_scheme.id,
                    "payment_provider_id": self.payment_provider.id,
                    "location": f"any location for {mid}",
                    "postcode": f"any post",
                },
            )
            if created:
                print(f"Created MID {mid}.")
            else:
                print(f"MID {mid} already exists.")

    def user_request_to_hermes(self):
        register_resp = requests.post(
            f"{HERMES_URL}/users/register", json={"email": f"{uuid4()}@txmatch.com", "password": "Password01"}
        )
        register_resp.raise_for_status()
        user_register_headers = {"Authorization": f"Token {register_resp.json()['api_key']}"}
        self.log.debug(f"User in Hermes has been registered: {register_resp.json()}")
        return user_register_headers

    def payment_card_request_to_hermes(self, user_register_headers, transaction):
        payment_card = ""
        try:
            payment_card = {
                "order": 0,
                "token": f"token-{b64encode(uuid4().bytes).decode()}",
                "name_on_card": "Test Card1",
                "expiry_month": "12",
                "expiry_year": "99",
                "currency_code": "GBP",
                "country": "UK",
                "pan_start": transaction["card"]["first_6"],
                "pan_end": transaction["card"]["last_4"],
                "fingerprint": f"token-{b64encode(uuid4().bytes).decode()}",
                "payment_card": 1,
            }
            pca_resp = requests.post(
                f"{HERMES_URL}/payment_cards/accounts", json=payment_card, headers=user_register_headers
            )
            pca_resp.raise_for_status()
            self.log.debug(f"Payment card in Hermes has been registered {pca_resp.json()}")
        except Exception as error:
            self.errors_in_processes.append(error)
        return payment_card

    def scheme_account_request_to_hermes(self, user_register_headers):
        scheme_card = str(uuid4())
        sa2_resp = requests.post(
            f"{HERMES_URL}/schemes/accounts",
            json={"order": 0, "scheme": 1, "card_number": scheme_card},
            headers=user_register_headers,
        )
        sa2_resp.raise_for_status()
        self.log.debug(f"Scheme account in Hermes has been registered {sa2_resp.json()}")
        return scheme_card, sa2_resp

    def credentials_request_to_hermes(self, sa2_resp, user_register_headers, scheme_card_number):
        credentials_json = {"password": "1234567", "email": "email=bv@gmail.com", "card_number": scheme_card_number}
        sa2_cred_resp = requests.put(
            f"{HERMES_URL}/schemes/accounts/{sa2_resp.json()['id']}/credentials",
            json=credentials_json,
            headers=user_register_headers,
        )
        sa2_cred_resp.raise_for_status()
        json_status = {"journey": "link", "status": 1}
        headers = {"Authorization": "Token F616CE5C88744DD52DB628FAD8B3D"}
        status_resp = requests.post(
            f"{HERMES_URL}/schemes/accounts/{sa2_resp.json()['id']}/status", json=json_status, headers=headers
        )
        status_resp.raise_for_status()

        status_resp = requests.post(
            f"{HERMES_URL}/schemes/accounts/{sa2_resp.json()['id']}/status", json=json_status, headers=headers
        )
        status_resp.raise_for_status()
        self.log.debug(f"Credentials in Hermes has been registered: {credentials_json}")

    def payment_request_to_harmonia(self, transaction, payment_card):
        requests.post(
            f"{HARMONIA_URL}/txm/import/bink-payment",
            json={
                "date": transaction["timestamp"],
                "mid": transaction["store_id"],
                "spend": int(float(transaction["amount"]["value"]) * 100),
                "tid": str(uuid4()),
                "token": payment_card["token"],
            },
        ).raise_for_status()

    def all_processes(self):
        file = self.create_input_file()
        self.add_all_mid(file["transactions"])
        print(f"There are {str(len(file['transactions']))} transactions to do.")

        for transaction in file["transactions"]:
            user_register_headers = self.user_request_to_hermes()
            payment_card = self.payment_card_request_to_hermes(user_register_headers, transaction)
            scheme_card_number, sa2_resp = self.scheme_account_request_to_hermes(user_register_headers)
            self.credentials_request_to_hermes(sa2_resp, user_register_headers, scheme_card_number)
            self.payment_request_to_harmonia(transaction, payment_card)


if __name__ == "__main__":
    cooperative = CooperativeProducer()
    cooperative.all_processes()
