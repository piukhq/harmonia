import csv
import inspect
import io
import typing as t
from decimal import Decimal

import pendulum

from app import db
from app.config import KEY_PREFIX, Config, ConfigValue
from app.currency import to_pennies
from app.feeds import ImportFeedTypes
from app.imports.agents.bases.base import SchemeTransactionFields
from app.imports.agents.bases.file_agent import FileAgent
from app.service.hermes import PaymentProviderSlug

PROVIDER_SLUG = "iceland-bonus-card"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"
SCHEDULE_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.schedule"

DATETIME_FORMAT = "YYYY-MM-DD HH:mm:ss"


class Iceland(FileAgent):
    feed_type = ImportFeedTypes.MERCHANT
    provider_slug = PROVIDER_SLUG

    field_transforms: t.Dict[str, t.Callable] = {
        "TransactionCardSchemeId": int,
        "TransactionAmountValue": lambda x: to_pennies(x),
        "TransactionCashbackValue": Decimal,
        "TransactionTimestamp": lambda x: pendulum.from_format(x, DATETIME_FORMAT, tz="Europe/London"),
    }

    payment_provider_map = {
        "Amex": PaymentProviderSlug.AMEX,
        "Visa": PaymentProviderSlug.VISA,
        "Visa Debit": PaymentProviderSlug.VISA,
        "Electron": PaymentProviderSlug.VISA,
        "Visa CPC": PaymentProviderSlug.VISA,
        "MasterCard/MasterCard One": PaymentProviderSlug.MASTERCARD,
        "Maestro": PaymentProviderSlug.MASTERCARD,
        "EDC/Maestro (INT) / Laser": PaymentProviderSlug.MASTERCARD,
        "MasterCard Debit": PaymentProviderSlug.MASTERCARD,
        "Mastercard One": PaymentProviderSlug.MASTERCARD,
        "Bink-Payment": "bink-payment",
    }

    config = Config(
        ConfigValue("path", key=PATH_KEY, default=f"{PROVIDER_SLUG}/"),
        ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *"),
    )

    def __init__(self):
        super().__init__()

        # Set up Prometheus metric types
        self.prometheus_metrics = {
            "counters": ["files_received", "transactions"],
            "gauges": ["last_file_timestamp"],
        }

    def yield_transactions_data(self, data: bytes) -> t.Iterable[dict]:
        fd = io.StringIO(data.decode())
        reader = csv.DictReader(fd)
        for raw_data in reader:
            if raw_data["TransactionAuthCode"].lower() == "decline":
                continue

            if raw_data["TransactionCardScheme"] not in self.payment_provider_map:
                continue

            yield {k: self.field_transforms.get(k, str)(v) for k, v in raw_data.items()}

    def help(self, session: db.Session) -> str:
        return inspect.cleandoc(
            f"""
            This is the Iceland payment transaction file import agent.

            It is currently set up to monitor {self.config.get("path", session=session)} for files to import.
            """
        )

    def to_transaction_fields(self, data: dict) -> SchemeTransactionFields:
        return SchemeTransactionFields(
            transaction_date=self.get_transaction_date(data),
            has_time=True,
            payment_provider_slug=Iceland.payment_provider_map[data["TransactionCardScheme"]],
            spend_amount=data["TransactionAmountValue"],
            spend_multiplier=100,
            spend_currency=data["TransactionAmountUnit"],
            auth_code=data["TransactionAuthCode"],
            first_six=data["TransactionCardFirst6"],
            last_four=data["TransactionCardLast4"],
            extra_fields={
                k: data[k]
                for k in (
                    "TransactionCardExpiry",
                    "TransactionCardSchemeId",
                    "TransactionCardScheme",
                    "TransactionCashbackValue",
                    "TransactionCashbackUnit",
                )
            },
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["TransactionId"]

    def get_mids(self, data: dict) -> t.List[str]:
        return [data["TransactionStore_Id"]]

    def get_transaction_date(self, data: dict) -> pendulum.DateTime:
        return data["TransactionTimestamp"]
