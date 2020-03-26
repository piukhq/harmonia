import inspect
import typing as t
from decimal import Decimal
from uuid import uuid4

import pendulum

from app import models
from app.config import KEY_PREFIX, ConfigValue
from app.feeds import ImportFeedTypes
from app.imports.agents import FileAgent, QueueAgent

PROVIDER_SLUG = "mastercard"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"

DATE_FORMAT = "YYYYMMDD"


class MastercardSettled(FileAgent):
    feed_type = ImportFeedTypes.PAYMENT
    provider_slug = PROVIDER_SLUG

    field_widths = [
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

    field_transforms: t.Dict[str, t.Callable] = {
        "transaction_amount": lambda x: int(Decimal(x) * 100),
        "transaction_date": lambda x: pendulum.from_format(x, DATE_FORMAT),
        "transaction_time": int,
    }

    class Config:
        path = ConfigValue(PATH_KEY, default=f"{PROVIDER_SLUG}/")

    def parse_line(self, line: str) -> dict:
        idx = 0
        data = {}
        for field, width in self.field_widths:
            data[field] = line[idx : idx + width].strip()
            idx += width
        return data

    def yield_transactions_data(self, data: bytes) -> t.Iterable[dict]:
        lines = data.decode().split("\n")[1:]  # the header line is discarded
        for line in lines:
            raw_data = self.parse_line(line)

            if raw_data["record_type"] != "D":
                continue

            yield {k: self.field_transforms.get(k, str)(v) for k, v in raw_data.items()}

    def help(self) -> str:
        return inspect.cleandoc(
            f"""
            This is the Mastercard payment transaction file import agent.

            It is currently set up to monitor {self.Config.path} for files to import.
            """
        )

    @staticmethod
    def to_queue_transaction(
        data: dict, merchant_identifier_ids: t.List[int], transaction_id: str
    ) -> models.PaymentTransaction:
        return models.PaymentTransaction(
            merchant_identifier_ids=merchant_identifier_ids,
            transaction_id=transaction_id,
            transaction_date=data["transaction_date"],
            spend_amount=data["transaction_amount"],
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
    def get_mids(data: dict) -> t.List[str]:
        return [data["merchant_id"]]


class MastercardAuth(QueueAgent):
    provider_slug = PROVIDER_SLUG

    # TODO: this needs to change to be an AUTH feed
    feed_type = ImportFeedTypes.PAYMENT

    @staticmethod
    def to_queue_transaction(
        data: dict, merchant_identifier_ids: t.List[int], transaction_id: str
    ) -> models.PaymentTransaction:
        return models.PaymentTransaction(
            merchant_identifier_ids=merchant_identifier_ids,
            transaction_id=transaction_id,
            transaction_date=pendulum.parse(data["time"]),
            spend_amount=int(Decimal(data["amount"]) * 100),
            spend_multiplier=100,
            spend_currency=data["currency_code"],
            card_token=data["payment_card_token"],
            extra_fields={"third_party_id": data["third_party_id"]},
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        # TODO: is this alright?
        return str(uuid4())

    @staticmethod
    def get_mids(data: dict) -> t.List[str]:
        return [data["mid"]]
