import csv
import inspect
import io
import typing as t

import pendulum

from app import db
from app.config import KEY_PREFIX, Config, ConfigValue
from app.currency import to_pennies
from app.feeds import ImportFeedTypes
from app.imports.agents import FileAgent, SchemeTransactionFields
from app.service.hermes import PaymentProviderSlug

PROVIDER_SLUG = "whsmith-rewards"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"
DATETIME_FORMAT = "YYYY-MM-DDTHH:mm:ss.SSS"
SCHEDULE_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.schedule"

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


class WhSmith(FileAgent):
    feed_type = ImportFeedTypes.MERCHANT
    provider_slug = PROVIDER_SLUG

    field_transforms: t.Dict[str, t.Callable] = {
        "datetime": lambda x: pendulum.from_format(x, DATETIME_FORMAT, tz="Europe/London"),
        "total": lambda x: to_pennies(x),
    }

    payment_provider_map = {
        "AMEX": PaymentProviderSlug.AMEX,
        "VISA": PaymentProviderSlug.VISA,
        "VISA DEBIT": PaymentProviderSlug.VISA,
        "MASTERCARD": PaymentProviderSlug.MASTERCARD,
        "Bink-Payment": "bink-payment",
    }

    config = Config(
        ConfigValue("path", key=PATH_KEY, default=f"{PROVIDER_SLUG}/"),
        ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *"),
    )

    def help(self, session: db.Session) -> str:
        return inspect.cleandoc(
            f"""
            This is the WHSmith scheme transaction file import agent.

            It is currently set up to monitor {self.config.get("path", session=session)} for files to import.
            """
        )

    def yield_transactions_data(self, data: bytes) -> t.Iterable[dict]:
        fd = io.StringIO(data.decode())
        reader = csv.DictReader(fd, fieldnames=DATA_FIELDS, delimiter="|")
        for raw_data in reader:
            yield {k: self.field_transforms.get(k, str)(v) for k, v in raw_data.items()}

    def to_transaction_fields(self, data: dict) -> SchemeTransactionFields:
        return SchemeTransactionFields(
            payment_provider_slug=WhSmith.payment_provider_map[data["card_type"]],
            transaction_date=self.get_transaction_date(data),
            has_time=True,
            spend_amount=data["total"],
            spend_multiplier=100,
            spend_currency=data["currency"],
            auth_code=data["auth_no"],
            last_four=data["card_masked_pan"],
            extra_fields={},
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["transaction_uuid"]

    def get_mids(self, data: dict) -> t.List[str]:
        store_id = data["store_id"]
        return self.storeid_mid_map.get(store_id, [store_id])

    def get_transaction_date(self, data: dict) -> pendulum.DateTime:
        return data["datetime"]
