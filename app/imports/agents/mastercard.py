import typing as t
import inspect
from decimal import Decimal

import pendulum
from marshmallow import Schema, fields

from app import models
from app.config import KEY_PREFIX, ConfigValue
from app.feeds import ImportFeedTypes
from app.imports.agents.bases.directory_watch_agent import DirectoryWatchAgent

from app.utils import PendulumField

PROVIDER_SLUG = "mastercard"
WATCH_DIRECTORY_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.watch_directory"

DATE_FORMAT = "YYYYMMDD"


class MastercardAgentTransactionSchema(Schema):
    record_type = fields.String(required=True)
    transaction_sequence_number = fields.String(required=True)
    bank_account_number = fields.String(required=True)
    transaction_amount = fields.Decimal(required=True)
    transaction_date = PendulumField(required=True, date_format=DATE_FORMAT)
    merchant_dba_name = fields.String(required=True)
    merchant_id = fields.String(required=True)
    location_id = fields.String(required=True)
    issuer_ica_code = fields.String(required=True)
    transaction_time = fields.Integer(required=True)
    bank_net_ref_number = fields.String(required=True)
    bank_customer_number = fields.String(required=True)
    aggregate_merchant_id = fields.String(required=True)

    @staticmethod
    def to_queue_transaction(
        data: dict, merchant_identifier_id: int, transaction_id: str
    ) -> models.PaymentTransaction:
        return models.PaymentTransaction(
            merchant_identifier_id=merchant_identifier_id,
            transaction_id=transaction_id,
            transaction_date=pendulum.instance(data["transaction_date"]),
            spend_amount=int(Decimal(data["transaction_amount"]) * 100),
            spend_multiplier=100,
            spend_currency="GBP",
            card_token=data["bank_customer_number"],
            extra_fields={
                k: data[k]
                for k in (
                    "record_type",
                    "bank_account_number",
                    "merchant_dba_name",
                    "location_id",
                    "issuer_ica_code",
                    "transaction_time",
                    "bank_net_ref_number",
                    "aggregate_merchant_id",
                )
            },
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["transaction_sequence_number"]

    @staticmethod
    def get_mid(data: dict) -> str:
        return data["merchant_id"]


class MastercardAgent(DirectoryWatchAgent):
    schema = MastercardAgentTransactionSchema()
    feed_type = ImportFeedTypes.PAYMENT
    provider_slug = PROVIDER_SLUG

    file_field_widths = [
        ("record_type", 1),
        ("transaction_sequence_number", 13),
        ("bank_account_number", 19),
        ("transaction_amount", 13),
        ("transaction_date", 8),
        ("merchant_dba_name", 60),
        ("merchant_id", 22),
        ("location_id", 9),
        ("issuer_ica_code", 6),
        ("transaction_time", 4),
        ("bank_net_ref_number", 9),
        ("bank_customer_number", 30),
        ("aggregate_merchant_id", 6),
    ]

    file_field_types = {"transaction_amount": Decimal, "transaction_time": int}

    class Config:
        watch_directory = ConfigValue(
            WATCH_DIRECTORY_KEY, default=f"files/imports/{PROVIDER_SLUG}"
        )

    def parse_line(self, line: str) -> dict:
        idx = 0
        data = {}
        for field, width in self.file_field_widths:
            data[field] = line[idx : idx + width].strip()
            idx += width
        return data

    def yield_transactions_data(self, fd: t.IO) -> t.Iterable[dict]:
        fd.readline()  # discard the header
        for line in fd.readlines():
            raw_data = self.parse_line(line)

            if raw_data["record_type"] != "D":
                continue

            yield {k: self.file_field_types.get(k, str)(v) for k, v in raw_data.items()}

    def help(self) -> str:
        return inspect.cleandoc(
            f"""
        This is the Mastercard payment transaction file import agent.

        It is currently set up to monitor {self.Config.watch_directory} for files to import.
        """
        )
