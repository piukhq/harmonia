import typing as t
import inspect
from hashlib import sha256

import pendulum

from app.config import KEY_PREFIX, ConfigValue
from app.feeds import ImportFeedTypes
from app.imports.agents import FileAgent, QueueAgent, PaymentTransactionFields
from app.currency import to_pennies

PROVIDER_SLUG = "amex"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"
QUEUE_NAME_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}-auth.queue_name"

DATE_FORMAT = "YYYY-MM-DD"
DATETIME_FORMAT = "YYYY-MM-DD-HH.mm.ss"


class SettlementKeyError(Exception):
    pass


def _make_settlement_key(
    *,
    card_token: str,
    transaction_id: t.Optional[str] = None,
    mid: t.Optional[str] = None,
    approval_code: t.Optional[str] = None,
    amount: t.Optional[str] = None,
):
    """
    auth-settled transaction pairing logic from amex:

    most transactions:
    settlement key = card token + transaction ID

    if transaction ID is blank:
    settlement key = card token + approval code + MID

    if approval code is blank:
    settlement key = card token + amount + MID
    """

    parts = ["amex", card_token]
    if transaction_id:
        parts.append(transaction_id)
    elif approval_code and mid:
        parts.append(approval_code)
        parts.append(mid)
    elif amount and mid:
        parts.append(amount)
        parts.append(mid)
    else:
        raise SettlementKeyError(
            "Failed to generate a settlement key. "
            "At least one of the following combinations must be provided: "
            "card token + transaction ID, "
            "card token + approval code + mid, or"
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
        "transaction_amount": lambda x: to_pennies(float(x)),
    }

    class Config:
        path = ConfigValue(PATH_KEY, default=f"{PROVIDER_SLUG}/")

    def help(self) -> str:
        return inspect.cleandoc(
            f"""
        This is the Amex payment transaction file import agent.

        It is currently set up to monitor {self.Config.path} for files to import.
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

    @staticmethod
    def get_mids(data: dict) -> t.List[str]:
        return [data["merchant_number"]]


class AmexAuth(QueueAgent):
    provider_slug = PROVIDER_SLUG
    feed_type = ImportFeedTypes.AUTH

    class Config:
        queue_name = ConfigValue(QUEUE_NAME_KEY, "amex-auth")

    @staticmethod
    def to_transaction_fields(data: dict) -> PaymentTransactionFields:
        # pendulum 2.1.0 has a type hint bug that suggests `parse` returns a string.
        # we can remove this fix when the bug is resolved.
        # https://github.com/sdispater/pendulum/pull/452
        transaction_date: pendulum.DateTime = pendulum.parse(data["transaction_time"], tz="MST")  # type: ignore
        amount = to_pennies(float(data["transaction_amount"]))
        settlement_key = _make_settlement_key(
            card_token=data["cm_alias"],
            transaction_id=data["transaction_id"],
            mid=data["merchant_number"],
            approval_code=data["approval_code"],
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
            auth_code=data["approval_code"],
            extra_fields={"offer_id": data["offer_id"]},
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["transaction_id"]

    @staticmethod
    def get_mids(data: dict) -> t.List[str]:
        return [data["merchant_number"]]
