import csv
import inspect
import io
import typing as t
from decimal import Decimal

import pendulum

from app.config import KEY_PREFIX, ConfigValue
from app.currency import to_pennies
from app.feeds import ImportFeedTypes
from app.imports.agents import FileAgent
from app.imports.agents.bases import base
from app.models import PaymentProviderSlug

PROVIDER_SLUG = "iceland-bonus-card"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"

DATETIME_FORMAT = "YYYY-MM-DD HH:mm:ss"


class Iceland(FileAgent):
    feed_type = ImportFeedTypes.MERCHANT
    provider_slug = PROVIDER_SLUG

    field_transforms: t.Dict[str, t.Callable] = {
        "TransactionCardSchemeId": int,
        "TransactionAmountValue": lambda x: to_pennies(float(x)),
        "TransactionCashbackValue": Decimal,
        "TransactionTimestamp": lambda x: pendulum.from_format(x, DATETIME_FORMAT),
    }

    payment_provider_map = {
        PaymentProviderSlug.AMEX: ("Amex",),
        PaymentProviderSlug.VISA: ("Visa", "Visa Debit", "Electron", "Visa CPC"),
        PaymentProviderSlug.MASTERCARD: (
            "MasterCard/MasterCard One",
            "Maestro",
            "EDC/Maestro (INT) / Laser",
            "MasterCard Debit",
            "Mastercard One",
        ),
        "no_card": ("No Card",),
        "bink-payment": ("Bink-Payment"),  # Testing only
    }

    class Config:
        path = ConfigValue(PATH_KEY, default=f"{PROVIDER_SLUG}/")

    def yield_transactions_data(self, data: bytes) -> t.Iterable[dict]:
        fd = io.StringIO(data.decode())
        reader = csv.DictReader(fd)
        for raw_data in reader:
            if raw_data["TransactionAuthCode"].lower() == "decline":
                continue

            yield {k: self.field_transforms.get(k, str)(v) for k, v in raw_data.items()}

    def help(self) -> str:
        return inspect.cleandoc(
            f"""
            This is the Iceland payment transaction file import agent.

            It is currently set up to monitor {self.Config.path} for files to import.
            """
        )

    @staticmethod
    def to_queue_transaction(data: dict) -> base.SchemeTransaction:
        return base.SchemeTransaction(
            transaction_date=data["TransactionTimestamp"],
            payment_provider_slug=Iceland._get_payment_scheme_provider(data["TransactionCardScheme"]),
            spend_amount=data["TransactionAmountValue"],
            spend_multiplier=100,
            spend_currency=data["TransactionAmountUnit"],
            points_amount="",
            points_multiplier="",
            extra_fields={
                k: data[k]
                for k in (
                    "TransactionCardFirst6",
                    "TransactionCardLast4",
                    "TransactionCardExpiry",
                    "TransactionCardSchemeId",
                    "TransactionCardScheme",
                    "TransactionCashbackValue",
                    "TransactionCashbackUnit",
                    "TransactionAuthCode",
                )
            },
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["TransactionId"]

    @staticmethod
    def get_mids(data: dict) -> t.List[str]:
        return [data["TransactionStore_Id"]]

    @staticmethod
    def _get_payment_scheme_provider(scheme_name: str) -> str:
        """
        Returns the payment scheme slug from the mapping of slugs to strings of possible scheme names in Iceland
        transaction files.
        """
        if not scheme_name or scheme_name in Iceland.payment_provider_map["no_card"]:
            return ""

        for slug, potential_values in Iceland.payment_provider_map.items():
            if scheme_name in potential_values:
                return slug
        return scheme_name
