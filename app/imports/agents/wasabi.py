import csv
import inspect
import io
import typing as t

from functools import cached_property

import pendulum

from app.config import KEY_PREFIX, ConfigValue
from app.currency import to_pennies
from app.feeds import ImportFeedTypes
from app.imports.agents.bases.base import SchemeTransactionFields
from app.imports.agents.bases.file_agent import ScheduledSftpFileAgent
from app.service.hermes import PaymentProviderSlug
from app.service.sftp import SFTPCredentials
from app.soteria import SoteriaConfigMixin

PROVIDER_SLUG = "wasabi-club"
SCHEDULE_KEY = f"{KEY_PREFIX}{PROVIDER_SLUG}.schedule"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"
DATE_FORMAT = "DD/MM/YYYY"
TIME_FORMAT = "HH:mm:ss"
TXN_DATETIME_FORMAT = f"{DATE_FORMAT} {TIME_FORMAT}"


class Wasabi(ScheduledSftpFileAgent, SoteriaConfigMixin):
    feed_type = ImportFeedTypes.MERCHANT
    provider_slug = PROVIDER_SLUG

    payment_provider_map = {
        "American Express": PaymentProviderSlug.AMEX,
        "Visa": PaymentProviderSlug.VISA,
        "Visa Debit": PaymentProviderSlug.VISA,
        "Mastercard": PaymentProviderSlug.MASTERCARD,
        "Debit Mastercard": PaymentProviderSlug.MASTERCARD,
        "Bink-Payment": "bink-payment",
    }

    class Config:
        path = ConfigValue(PATH_KEY, default="/")
        schedule = ConfigValue(SCHEDULE_KEY, "* * * * *")

    @cached_property
    def _security_credentials(self) -> dict:
        config = self.get_soteria_config()
        return {
            c["credential_type"]: c["value"]
            for c in config.security_credentials["inbound"]["credentials"]
        }

    @cached_property
    def sftp_credentials(self) -> SFTPCredentials:  # type: ignore
        compound_key = self._security_credentials["compound_key"]
        return SFTPCredentials(**{k: compound_key[k] for k in SFTPCredentials._fields})

    @cached_property
    def skey(self) -> t.Optional[io.StringIO]:  # type: ignore
        skey = self._security_credentials.get("bink_private_key")
        return io.StringIO(skey) if skey else None

    def help(self) -> str:
        return inspect.cleandoc(
            f"""
            This is the Wasabi scheme transaction SFTP file import agent.

            It is currently set up to monitor {self.Config.path} on SFTP host {self.sftp_credentials.host}
            for files to import.
            """
        )

    def yield_transactions_data(self, data: bytes) -> t.Iterable[dict]:
        fd = io.StringIO(data.decode())
        reader = csv.DictReader(fd)
        for raw_data in reader:
            yield {k: v for k, v in raw_data.items()}

    @staticmethod
    def to_transaction_fields(data: dict) -> SchemeTransactionFields:
        transaction_date_time = f"{data['Date']} {data['Time']}"
        transaction_date = pendulum.from_format(
            transaction_date_time, TXN_DATETIME_FORMAT, tz="Europe/London"
        )
        return SchemeTransactionFields(
            payment_provider_slug=Wasabi.payment_provider_map[data["Card Type Name"]],
            transaction_date=transaction_date,
            has_time=True,
            spend_amount=to_pennies(data["Amount"]),
            spend_multiplier=100,
            spend_currency="GBP",
            auth_code=data["Auth_code"],
            extra_fields={
                "first_six": data["Card Number"][:6],
                "last_four": data["Card Number"][-4:],
            },
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        """
        For Wasabi we need to take the Receipt No as this is the unique field, rather than Transaction No
        """
        return data["Receipt No_"]

    @staticmethod
    def get_mids(data: dict) -> t.List[str]:
        return [data["EFT Merchant No_"]]
