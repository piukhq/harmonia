import typing as t
import inspect
from hashlib import sha256

import pendulum
from app import db
from app.config import KEY_PREFIX, Config, ConfigValue
from app.feeds import ImportFeedTypes
from app.imports.agents import FileAgent, QueueAgent, PaymentTransactionFields
from app.currency import to_pennies

PROVIDER_SLUG = "amex"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"
QUEUE_NAME_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}-auth.queue_name"
SCHEDULE_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.schedule"

DATE_FORMAT = "YYYY-MM-DD"
DATETIME_FORMAT = "YYYY-MM-DD-HH.mm.ss"


class SettlementKeyError(Exception):
    pass


def _make_settlement_key(
    *,
    card_token: str,
    transaction_id: t.Optional[str] = None,
    mid: t.Optional[str] = None,
    amount: t.Optional[str] = None,
):
    """
    auth-settled transaction pairing logic from amex:

    most transactions:
    settlement key = card token + transaction ID

    if transaction ID is blank:
    settlement key = card token + amount + MID
    """

    parts = ["amex", card_token]
    if transaction_id:
        parts.append(transaction_id)
    elif amount and mid:
        parts.append(amount)
        parts.append(mid)
    else:
        raise SettlementKeyError(
            "Failed to generate a settlement key. "
            "At least one of the following combinations must be provided: "
            "card token + transaction ID, or"
            "card_token + amount + mid. "
            "This transaction has not been imported."
        )

    return sha256(".".join(parts).encode()).hexdigest()


class Amex(FileAgent):
    feed_type = ImportFeedTypes.SETTLED
    provider_slug = PROVIDER_SLUG

    file_fields = [
        "detail_identifier",
        "partner_id",
        "transaction_id",
        "purchase_date",
        "transaction_amount",
        "card_token",
        "merchant_number",
        "transaction_date",
        "alias_card_number",
    ]

    field_transforms: t.Dict[str, t.Callable] = {
        "purchase_date": lambda x: pendulum.from_format(x, DATE_FORMAT, tz="Europe/London"),
        "transaction_date": lambda x: pendulum.from_format(x, DATETIME_FORMAT, tz="Europe/London"),
        "transaction_amount": lambda x: to_pennies(x),
    }

    config = Config(
        ConfigValue("path", key=PATH_KEY, default=f"{PROVIDER_SLUG}/"),
        ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *"),
    )

    def help(self, session: db.Session) -> str:
        return inspect.cleandoc(
            f"""
        This is the Amex payment transaction file import agent.

        It is currently set up to monitor {self.config.get("path", session=session)} for files to import.
        """
        )

    def yield_transactions_data(self, data: bytes) -> t.Iterable[dict]:
        for line in data.decode().split("\n"):
            raw_data = [ln.strip() for ln in line.split("|")]

            if not raw_data or raw_data[0] != "D":
                continue

            yield {k: self.field_transforms.get(k, str)(v) for k, v in zip(self.file_fields, raw_data)}

    def to_transaction_fields(self, data: dict) -> PaymentTransactionFields:
        settlement_key = _make_settlement_key(
            card_token=data["card_token"],
            transaction_id=data["transaction_id"],
            mid=data["merchant_number"],
            amount=str(data["transaction_amount"]),
        )
        return PaymentTransactionFields(
            settlement_key=settlement_key,
            transaction_date=data["transaction_date"],
            has_time=True,
            spend_amount=data["transaction_amount"],
            spend_multiplier=100,
            spend_currency="GBP",
            card_token=data["card_token"],
            extra_fields={
                k: data[k] for k in ("detail_identifier", "partner_id", "purchase_date", "alias_card_number")
            },
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["transaction_id"]

    def get_mids(self, data: dict) -> t.List[str]:
        return [data["merchant_number"]]


class AmexAuth(QueueAgent):
    provider_slug = PROVIDER_SLUG
    feed_type = ImportFeedTypes.AUTH

    config = Config(ConfigValue("queue_name", key=QUEUE_NAME_KEY, default="amex-auth"))

    def to_transaction_fields(self, data: dict) -> PaymentTransactionFields:
        transaction_date = self.pendulum_parse(data["transaction_time"], tz="MST")
        amount = to_pennies(data["transaction_amount"])
        settlement_key = _make_settlement_key(
            card_token=data["cm_alias"],
            transaction_id=data["transaction_id"],
            mid=data["merchant_number"],
            amount=str(amount),
        )

        return PaymentTransactionFields(
            settlement_key=settlement_key,
            transaction_date=transaction_date,
            has_time=True,
            spend_amount=amount,
            spend_multiplier=100,
            spend_currency="GBP",
            card_token=data["cm_alias"],
            extra_fields={"offer_id": data["offer_id"]},
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["transaction_id"]

    def get_mids(self, data: dict) -> t.List[str]:
        return [data["merchant_number"]]
