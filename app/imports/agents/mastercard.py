import typing as t
from hashlib import sha256
from uuid import uuid4

import pendulum

from app.config import KEY_PREFIX, Config, ConfigValue
from app.currency import to_pennies
from app.feeds import FeedType
from app.imports.agents.bases.base import PaymentTransactionFields
from app.imports.agents.bases.file_agent import FileAgent
from app.imports.agents.bases.queue_agent import QueueAgent

PROVIDER_SLUG = "mastercard"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}-settled.path"
QUEUE_NAME_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}-auth.queue_name"
SCHEDULE_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.schedule"

DATE_FORMAT = "YYYYMMDD"
TIME_FORMAT = "HHmm"
DATETIME_FORMAT = f"{DATE_FORMAT} {TIME_FORMAT}"


class FixedWidthField(t.NamedTuple):
    name: str
    start: int
    length: int


def _make_settlement_key(*, third_party_id: t.Optional[str], transaction_date: pendulum.DateTime, mid: str, token: str):
    hash_parts = [
        third_party_id if third_party_id else str(uuid4()),
        transaction_date.date().isoformat(),
        mid,
        token,
    ]
    return sha256(f"mastercard.{'.'.join(hash_parts)}".encode()).hexdigest()


def try_convert_settlement_mid(mid: str) -> str:
    prefix = "0000000"
    if mid.startswith(prefix):
        return mid[len(prefix) :]
    return mid


class MastercardTS44Settlement(FileAgent):
    feed_type = FeedType.SETTLED
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

    def to_transaction_fields(self, data: dict) -> PaymentTransactionFields:
        transaction_date = self.get_transaction_date(data)
        card_token = data["bank_customer_number"]
        return PaymentTransactionFields(
            merchant_slug=self.get_merchant_slug(data),
            payment_provider_slug=self.provider_slug,
            settlement_key=_make_settlement_key(
                third_party_id=data["bank_net_ref_number"],
                transaction_date=transaction_date,
                mid=data["merchant_id"],
                token=card_token,
            ),
            transaction_date=transaction_date,
            has_time=True,
            spend_amount=data["transaction_amount"],
            spend_multiplier=100,
            spend_currency="GBP",
            card_token=card_token,
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["transaction_sequence_number"]

    def get_mids(self, data: dict) -> list[str]:
        return [data["mid"]]

    def get_transaction_date(self, data: dict) -> pendulum.DateTime:
        date_string = f"{data['transaction_date']} {data['transaction_time']}"
        return pendulum.from_format(date_string, DATETIME_FORMAT, tz="Europe/London")


class MastercardTGX2Settlement(FileAgent):
    provider_slug = PROVIDER_SLUG
    feed_type = FeedType.SETTLED

    config = Config(
        ConfigValue("path", key=PATH_KEY, default=f"{PROVIDER_SLUG}/"),
        ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *"),
    )

    # the "start" of these fields must be one less than in the documentation, because the lines are 0-indexed.
    fields = [
        FixedWidthField(name="record_type", start=0, length=1),
        FixedWidthField(name="mid", start=451, length=15),
        FixedWidthField(name="location_id", start=500, length=12),
        FixedWidthField(name="aggregate_merchant_id", start=512, length=6),
        FixedWidthField(name="amount", start=518, length=12),
        FixedWidthField(name="date", start=102, length=8),
        FixedWidthField(name="time", start=563, length=4),
        FixedWidthField(name="token", start=21, length=30),
        FixedWidthField(name="transaction_id", start=761, length=9),
        FixedWidthField(name="auth_code", start=567, length=6),
    ]

    field_transforms: t.Dict[str, t.Callable] = {
        "amount": int,
    }

    def parse_line(self, line: str) -> dict:
        return {field.name: line[field.start : field.start + field.length].strip() for field in self.fields}

    def yield_transactions_data(self, data: bytes) -> t.Iterable[dict]:
        lines = data.decode().split("\n")[1:]  # the header line is discarded
        for line in lines:
            raw_data = self.parse_line(line)

            if raw_data["record_type"] != "D":
                continue

            # raising an error for bad datetime format at this point allows the rest of the file to be imported.
            self.get_transaction_date(raw_data)

            yield {k: self.field_transforms.get(k, str)(v) for k, v in raw_data.items()}

    def to_transaction_fields(self, data: dict) -> PaymentTransactionFields:
        transaction_date = self.get_transaction_date(data)
        card_token = data["token"]
        return PaymentTransactionFields(
            merchant_slug=self.get_merchant_slug(data),
            payment_provider_slug=self.provider_slug,
            settlement_key=_make_settlement_key(
                third_party_id=data["transaction_id"],
                transaction_date=transaction_date,
                mid=data["mid"],
                token=card_token,
            ),
            transaction_date=transaction_date,
            has_time=True,
            spend_amount=data["amount"],
            spend_multiplier=100,
            spend_currency="GBP",
            card_token=card_token,
            auth_code=data["auth_code"],
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        if transaction_id := data.get("transaction_id"):
            return transaction_id
        else:
            return uuid4().hex

    def get_mids(self, data: dict) -> list[str]:
        return [data["mid"], data["location_id"], data["aggregate_merchant_id"]]

    def get_transaction_date(self, data: dict) -> pendulum.DateTime:
        date_string = f"{data['date']} {data['time']}"
        return pendulum.from_format(date_string, DATETIME_FORMAT, tz="Europe/London")


class MastercardAuth(QueueAgent):
    provider_slug = PROVIDER_SLUG
    feed_type = FeedType.AUTH

    config = Config(ConfigValue("queue_name", key=QUEUE_NAME_KEY, default="mastercard-auth"))

    def to_transaction_fields(self, data: dict) -> PaymentTransactionFields:
        transaction_date = self.pendulum_parse(data["time"], tz="Europe/London")
        card_token = data["payment_card_token"]
        return PaymentTransactionFields(
            merchant_slug=self.get_merchant_slug(data),
            payment_provider_slug=self.provider_slug,
            settlement_key=_make_settlement_key(
                third_party_id=data["third_party_id"],
                transaction_date=transaction_date,
                mid=data["mid"],
                token=card_token,
            ),
            transaction_date=transaction_date,
            has_time=True,
            spend_amount=to_pennies(data["amount"]),
            spend_multiplier=100,
            spend_currency=data["currency_code"],
            card_token=card_token,
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return uuid4().hex

    def get_mids(self, data: dict) -> list[str]:
        return [data["mid"]]
