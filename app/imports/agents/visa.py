import inspect
import typing as t
from pathlib import Path
from hashlib import sha256

import gnupg
import pendulum

from app.config import KEY_PREFIX, ConfigValue
from app.core import key_manager
from app.currency import to_pennies
from app.feeds import ImportFeedTypes
from app.imports.agents import FileAgent, QueueAgent, PaymentTransactionFields
import settings

PROVIDER_SLUG = "visa"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"

DATE_FORMAT = "YYYYMMDD"


def _make_settlement_key(key_id: str):
    return sha256(f"visa.{key_id}".encode()).hexdigest()


def get_key_value(data: dict, key: str):
    for d in data["MessageElementsCollection"]:
        if d["Key"] == key:
            return d["Value"]


class Visa(FileAgent):
    feed_type = ImportFeedTypes.SETTLED
    provider_slug = PROVIDER_SLUG
    file_open_mode = "rb"

    field_widths = [
        ("record_type", 2),
        ("record_subtype", 2),
        ("promotion_code", 27),
        ("transaction_code", 2),
        ("transaction_amount", 15),
        ("filler1", 21),
        ("project_sponsor_id", 6),
        ("promotion_group_id", 6),
        ("filler2", 34),
        ("merchant_description_name", 25),
        ("merchant_city", 13),
        ("merchant_state", 2),
        ("merchant_zip", 9),
        ("merchant_country", 4),
        ("purchase_date", 8),
        ("filler3", 18),
        ("card_acceptor_id", 15),
        ("transaction_date", 8),
        ("transaction_time", 4),
        ("filler4", 16),
        ("central_processing_date", 8),
        ("transaction_sequence_id", 14),
        ("filler5", 108),
        ("country_currency_code", 3),
        ("acquirer_transaction_amount", 15),
        ("acquirer_currency_code", 3),
        ("filler6", 44),
        ("transaction_id", 15),
        ("filler7", 22),
        ("authorisation_code", 6),
        ("filler8", 89),
        ("external_card_holder_id", 25),
        ("transaction_gmt_time", 4),
    ]

    field_transforms: t.Dict[str, t.Callable] = {
        "transaction_amount": int,
        "purchase_date": lambda x: pendulum.from_format(x, DATE_FORMAT, tz="GMT"),
        "transaction_date": lambda x: pendulum.from_format(x, DATE_FORMAT, tz="GMT"),
        "acquirer_transaction_amount": int,
    }

    class Config:
        path = ConfigValue(PATH_KEY, default=f"{PROVIDER_SLUG}/")

    def help(self) -> str:
        return inspect.cleandoc(
            f"""
            This is the Visa payment transaction file import agent.

            It is currently set up to monitor {self.Config.path} for files to import.
            """
        )

    def parse_line(self, line: str) -> dict:
        idx = 0
        data = {}
        for field, width in self.field_widths:
            data[field] = line[idx : idx + width].strip()
            idx += width
        return data

    @staticmethod
    def _download_key(path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        manager = key_manager.KeyManager()
        key_data = manager.read_key(PROVIDER_SLUG)
        with path.open("wb") as f:
            f.write(key_data)

    @staticmethod
    def _get_key():
        key_path = Path(settings.GPG_ARGS["gnupghome"]) / PROVIDER_SLUG
        if not key_path.exists():
            Visa._download_key(key_path)
        with key_path.open("rb") as f:
            return f.read()

    def _decrypt_data(self, data: bytes) -> str:
        key = self._get_key()
        gpg = gnupg.GPG(**settings.GPG_ARGS)
        gpg.import_keys(key)
        result = gpg.decrypt(data)
        if not result.ok:
            raise self.ImportError(f"Decryption failed: {result.stderr}")
        return str(result)

    def yield_transactions_data(self, data: bytes) -> t.Iterable[dict]:
        if settings.VISA_ENCRYPTED:
            file_data = self._decrypt_data(data)
        else:
            file_data = data.decode()

        lines = file_data.split("\n")
        for line in lines:
            if not line.startswith("1601"):
                continue

            raw_data = self.parse_line(line)

            yield {k: self.field_transforms.get(k, str)(v) for k, v in raw_data.items()}

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["transaction_id"]

    @staticmethod
    def get_mids(data: dict) -> t.List[str]:
        return [data["card_acceptor_id"]]

    @staticmethod
    def to_transaction_fields(data: dict) -> PaymentTransactionFields:
        return PaymentTransactionFields(
            settlement_key=_make_settlement_key(data["transaction_id"]),
            transaction_date=data["transaction_date"],
            has_time=True,
            spend_amount=data["transaction_amount"],
            spend_multiplier=100,
            spend_currency=data["country_currency_code"],
            card_token=data["external_card_holder_id"],
            auth_code=data["authorisation_code"],
            extra_fields={k: data[k] for k in ("merchant_description_name", "merchant_city")},
        )


class VisaAuth(QueueAgent):
    provider_slug = PROVIDER_SLUG
    feed_type = ImportFeedTypes.AUTH

    class Config:
        QUEUE_NAME_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}-auth.queue_name"
        queue_name = ConfigValue(QUEUE_NAME_KEY, "visa-auth")

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return get_key_value(data, "Transaction.VipTransactionId")

    @staticmethod
    def get_mids(data: dict) -> t.List[str]:
        return [get_key_value(data, "Transaction.MerchantCardAcceptorId")]

    def to_transaction_fields(self, data: dict) -> PaymentTransactionFields:
        ext_user_id = data["ExternalUserId"]
        transaction_date = self.pendulum_parse(get_key_value(data, "Transaction.TimeStampYYMMDD"), tz="GMT")
        return PaymentTransactionFields(
            transaction_date=transaction_date,
            has_time=True,
            spend_amount=to_pennies(get_key_value(data, "Transaction.TransactionAmount")),
            spend_multiplier=100,
            spend_currency="GBP",
            card_token=ext_user_id,
            settlement_key=_make_settlement_key(get_key_value(data, "Transaction.VipTransactionId")),
            auth_code=get_key_value(data, "Transaction.AuthCode"),
            extra_fields={},
        )


class VisaSettlement(QueueAgent):
    provider_slug = PROVIDER_SLUG
    feed_type = ImportFeedTypes.AUTH

    class Config:
        QUEUE_NAME_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}-settlement.queue_name"
        queue_name = ConfigValue(QUEUE_NAME_KEY, "visa-settlement")

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return get_key_value(data, "Transaction.VipTransactionId")

    @staticmethod
    def get_mids(data: dict) -> t.List[str]:
        return [get_key_value(data, "Transaction.MerchantCardAcceptorId")]

    def to_transaction_fields(self, data: dict) -> PaymentTransactionFields:
        ext_user_id = data["ExternalUserId"]
        transaction_date = self.pendulum_parse(get_key_value(data, "Transaction.MerchantDateTimeGMT"), tz="GMT")
        return PaymentTransactionFields(
            transaction_date=transaction_date,
            has_time=True,
            spend_amount=to_pennies(get_key_value(data, "Transaction.SettlementAmount")),
            spend_multiplier=100,
            spend_currency="GBP",
            card_token=ext_user_id,
            settlement_key=_make_settlement_key(get_key_value(data, "Transaction.VipTransactionId")),
            auth_code=get_key_value(data, "Transaction.AuthCode"),
            extra_fields={},
        )
