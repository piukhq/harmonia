import inspect
import typing as t
from uuid import uuid4
from hashlib import sha256

import pendulum

from app import db
from app.config import KEY_PREFIX, Config, ConfigValue
from app.feeds import ImportFeedTypes
from app.imports.agents import FileAgent, QueueAgent, PaymentTransactionFields
from app.currency import to_pennies

PROVIDER_SLUG = "mastercard"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}-settled.path"
QUEUE_NAME_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}-auth.queue_name"
SCHEDULE_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.schedule"

DATE_FORMAT = "YYYYMMDD"


def _make_settlement_key(third_party_id: str):
    return sha256(f"mastercard.{third_party_id}".encode()).hexdigest()


class MastercardSettled(FileAgent):
    feed_type = ImportFeedTypes.SETTLED
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
        "transaction_amount": lambda x: to_pennies(x),
        "transaction_date": lambda x: pendulum.from_format(x, DATE_FORMAT),
        "transaction_time": int,
    }

    config = Config(
        ConfigValue("path", key=PATH_KEY, default=f"{PROVIDER_SLUG}/"),
        ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *"),
    )

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

    def help(self, session: db.Session) -> str:
        return inspect.cleandoc(
            f"""
            This is the Mastercard payment transaction file import agent.

            It is currently set up to monitor {self.config.get("path", session=session)} for files to import.
            """
        )

    @staticmethod
    def to_transaction_fields(data: dict) -> PaymentTransactionFields:
        return PaymentTransactionFields(
            settlement_key=_make_settlement_key(data["bank_net_ref_number"]),
            transaction_date=data["transaction_date"],
            has_time=False,
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

    def get_mids(self, data: dict) -> t.List[str]:
        return [data["merchant_id"]]


class MastercardAuth(QueueAgent):
    provider_slug = PROVIDER_SLUG
    feed_type = ImportFeedTypes.AUTH

    config = Config(ConfigValue("queue_name", key=QUEUE_NAME_KEY, default="mastercard-auth"))

    def to_transaction_fields(self, data: dict) -> PaymentTransactionFields:
        transaction_date = self.pendulum_parse(data["time"], tz="Europe/London")
        return PaymentTransactionFields(
            settlement_key=_make_settlement_key(data["third_party_id"]),
            transaction_date=transaction_date,
            has_time=True,
            spend_amount=to_pennies(data["amount"]),
            spend_multiplier=100,
            spend_currency=data["currency_code"],
            card_token=data["payment_card_token"],
            extra_fields={"third_party_id": data["third_party_id"]},
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        # TODO: is this alright?
        return str(uuid4())

    def get_mids(self, data: dict) -> t.List[str]:
        return [data["mid"]]
