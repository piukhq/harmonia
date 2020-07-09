import csv
import inspect
import io
import typing as t

import pendulum

from app.config import KEY_PREFIX, ConfigValue
from app.currency import to_pennies
from app.feeds import ImportFeedTypes
from app.imports.agents import FileAgent, SchemeTransactionFields
from app.service.hermes import PaymentProviderSlug

PROVIDER_SLUG = "whsmith-rewards"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"
DATETIME_FORMAT = "YYYY-MM-DDTHH:mm:ss.SSS"

DATA_FIELDS = (
    "transaction_uuid",
    "receipt_id",
    "datetime",
    "unix_datetime",
    "store_id",
    "store_name",
    "store_brand",
    "pos_id",
    "sequence_number",
    "operator_name",
    "operator_id",
    "ecrebo_hash_token",
    "loyalty_id",
    "purchase_quantity",
    "total",
    "tender_cash",
    "tender_card",
    "card_masked_pan",
    "card_type",
    "card_expiry",
    "auth_no",
    "merchant_id",
    "aid",
    "currency",
    "country",
)

STORE_ID_TO_MIDS = {
    # FIXME: Full store ID to MID mapping required
    "5842": ["942424905", "61584292"]
}


class WhSmith(FileAgent):
    feed_type = ImportFeedTypes.MERCHANT
    provider_slug = PROVIDER_SLUG

    field_transforms: t.Dict[str, t.Callable] = {
        "datetime": lambda x: pendulum.from_format(x, DATETIME_FORMAT, tz="Europe/London"),
        "total": lambda x: to_pennies(float(x)),
    }

    payment_provider_map = {
        "AMEX": PaymentProviderSlug.AMEX,
        "VISA": PaymentProviderSlug.VISA,
        "VISA DEBIT": PaymentProviderSlug.VISA,
        "MASTERCARD": PaymentProviderSlug.MASTERCARD,
        "Bink-Payment": "bink-payment",
    }

    class Config:
        path = ConfigValue(PATH_KEY, default=f"{PROVIDER_SLUG}/")

    def help(self) -> str:
        return inspect.cleandoc(
            f"""
            This is the WHSmith scheme transaction file import agent.

            It is currently set up to monitor {self.Config.path} for files to import.
            """
        )

    def yield_transactions_data(self, data: bytes) -> t.Iterable[dict]:
        fd = io.StringIO(data.decode())
        reader = csv.DictReader(fd, fieldnames=DATA_FIELDS, delimiter="|")
        for raw_data in reader:
            yield {k: self.field_transforms.get(k, str)(v) for k, v in raw_data.items()}

    @staticmethod
    def to_transaction_fields(data: dict) -> SchemeTransactionFields:
        return SchemeTransactionFields(
            payment_provider_slug=WhSmith.payment_provider_map[data["card_type"]],
            transaction_date=data["datetime"],
            has_time=True,
            spend_amount=data["total"],
            spend_multiplier=100,
            spend_currency=data["currency"],
            auth_code=data["auth_no"],
            extra_fields={"last_four": data["card_masked_pan"]},
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["transaction_uuid"]

    @staticmethod
    def get_mids(data: dict) -> t.List[str]:
        mid = data["store_id"]
        return STORE_ID_TO_MIDS.get(mid, [mid])
