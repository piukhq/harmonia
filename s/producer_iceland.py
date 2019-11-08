#! /usr/bin/env python3
import os
import csv
import requests
import settings

from app import models
from uuid import uuid4
from s import s_settings
from decimal import Decimal
from base64 import b64encode
from app.db import Base, session
from s.seed import get_or_create
from collections import OrderedDict
from app.reporting import get_logger

HERMES_URL = settings.HERMES_URL
LOYALTY_SCHEME_SLUG = "iceland-bonus-card"
PAYMENT_PROVIDER_SLUG = "bink-payment"
HARMONIA_URL = s_settings.HARMONIA_URL
ICELAND_FILE_WITH_TRANSACTIONS_PATH = s_settings.ICELAND_FILE_WITH_TRANSACTIONS_PATH
ICELAND_LIMIT_TRANSACTIONS_FROM_FILE = int(s_settings.ICELAND_LIMIT_TRANSACTIONS_FROM_FILE)


MOCK_TRANSACTIONS = [
    OrderedDict(
        [
            ("TransactionCardFirst6", "446238"),
            ("TransactionCardLast4", "9359"),
            ("TransactionCardExpiry", "01/21"),
            ("TransactionCardSchemeId", "6"),
            ("TransactionCardScheme", "Visa Debit"),
            ("TransactionStore_Id", "35573492"),
            ("TransactionTimestamp", "2019-10-24 10:47:19"),
            ("TransactionAmountValue", "7.1"),
            ("TransactionAmountUnit", "GBP"),
            ("TransactionCashbackValue", ".00"),
            ("TransactionCashbackUnit", "GBP"),
            ("TransactionId", "0000943_YF4OTBJP37"),
            ("TransactionAuthCode", "024672"),
        ]
    ),
    OrderedDict(
        [
            ("TransactionCardFirst6", "475129"),
            ("TransactionCardLast4", "1591"),
            ("TransactionCardExpiry", "04/23"),
            ("TransactionCardSchemeId", "6"),
            ("TransactionCardScheme", "Visa Debit"),
            ("TransactionStore_Id", "96553073"),
            ("TransactionTimestamp", "2019-10-23 16:27:33"),
            ("TransactionAmountValue", "12.80"),
            ("TransactionAmountUnit", "GBP"),
            ("TransactionCashbackValue", ".00"),
            ("TransactionCashbackUnit", "GBP"),
            ("TransactionId", "0003975_7KB63BB6Y7"),
            ("TransactionAuthCode", "273448"),
        ]
    ),
]


def get(model: Base, query: list) -> Base:
    return session.query(model).filter(*query).one()


class IcelandProducer(object):
    def __init__(self) -> None:
        self.log = get_logger(f"iceland-processes")

    errors_in_processes = []

    loyalty_scheme = get(models.LoyaltyScheme, query=[models.LoyaltyScheme.slug == LOYALTY_SCHEME_SLUG])
    payment_provider = get(models.PaymentProvider, query=[models.PaymentProvider.slug == PAYMENT_PROVIDER_SLUG])

    def read_data_from_file(self, file_path):
        with open(file_path, "r") as csv_data_file:
            csv_data = csv.DictReader(csv_data_file)
            return [x for x in csv_data]

    def save_harmonia_import_file(self, csv_data, file_type):
        import_file_path = f"../harmonia/files/imports/iceland-bonus-card/iceland_mock_transactions_{file_type}.csv"
        with open(import_file_path, "w", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(csv_data[0].keys())
            for row in csv_data[:ICELAND_LIMIT_TRANSACTIONS_FROM_FILE]:
                writer.writerow(row.values())

    def create_input_harmonia_file(self):
        if os.path.isfile(ICELAND_FILE_WITH_TRANSACTIONS_PATH):
            csv_data = self.read_data_from_file(ICELAND_FILE_WITH_TRANSACTIONS_PATH)
            self.save_harmonia_import_file(csv_data, "from_file")
            return csv_data

        else:
            self.save_harmonia_import_file(MOCK_TRANSACTIONS, "mock_data")
            return MOCK_TRANSACTIONS

    def add_all_mid(self, transactions):
        all_mids = []
        for transaction in transactions:
            try:
                all_mids.append(transaction["TransactionStore_Id"])
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
                "expiry_month": transaction["TransactionCardExpiry"][:2],
                "expiry_year": transaction["TransactionCardExpiry"][-2:],
                "currency_code": "GBP",
                "country": "UK",
                "pan_start": transaction["TransactionCardFirst6"],
                "pan_end": transaction["TransactionCardLast4"],
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
                "date": transaction["TransactionTimestamp"],
                "mid": transaction["TransactionStore_Id"],
                "spend": int(Decimal(transaction["TransactionAmountValue"]) * 100),
                "tid": str(uuid4()),
                "token": payment_card["token"],
            },
        ).raise_for_status()

    def all_processes(self):
        file = self.create_input_harmonia_file()[:ICELAND_LIMIT_TRANSACTIONS_FROM_FILE]
        self.add_all_mid(file)

        for transaction in file:
            user_register_headers = self.user_request_to_hermes()
            payment_card = self.payment_card_request_to_hermes(user_register_headers, transaction)
            scheme_card_number, sa2_resp = self.scheme_account_request_to_hermes(user_register_headers)
            self.credentials_request_to_hermes(sa2_resp, user_register_headers, scheme_card_number)
            self.payment_request_to_harmonia(transaction, payment_card)


if __name__ == "__main__":
    iceland = IcelandProducer()
    iceland.all_processes()
