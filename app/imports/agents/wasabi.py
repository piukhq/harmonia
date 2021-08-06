import csv
import inspect
import io
import typing as t
from functools import cached_property
from pathlib import Path

import pendulum
from app import db
from app.config import KEY_PREFIX, Config, ConfigValue
from app.currency import to_pennies
from app.feeds import ImportFeedTypes
from app.imports.agents.bases.base import SchemeTransactionFields
from app.imports.agents.bases.file_agent import (
    FileAgent,
    FileSourceBase,
    SftpFileSource,
)
from app.service.hermes import PaymentProviderSlug
from app.service.sftp import SFTPCredentials
from app.soteria import SoteriaConfigMixin

PROVIDER_SLUG = "wasabi-club"
SCHEDULE_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.schedule"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"
DATE_FORMAT = "DD/MM/YYYY"
TIME_FORMAT = "HH:mm:ss"
TXN_DATETIME_FORMAT = f"{DATE_FORMAT} {TIME_FORMAT}"


class Wasabi(FileAgent, SoteriaConfigMixin):
    feed_type = ImportFeedTypes.MERCHANT
    provider_slug = PROVIDER_SLUG

    payment_provider_map = {
        "American Express": PaymentProviderSlug.AMEX,
        "Visa": PaymentProviderSlug.VISA,
        "Visa Debit": PaymentProviderSlug.VISA,
        "Visa (Purchasing Card)": PaymentProviderSlug.VISA,
        "Visa (Enhanced Management Info": PaymentProviderSlug.VISA,
        "Mastercard": PaymentProviderSlug.MASTERCARD,
        "Maestro": PaymentProviderSlug.MASTERCARD,
        "Debit Mastercard": PaymentProviderSlug.MASTERCARD,
        "Compliments Card": PaymentProviderSlug.MASTERCARD,
        "Bink-Payment": "bink-payment",
    }

    config = Config(
        ConfigValue("path", key=PATH_KEY, default="/"), ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *")
    )

    def __init__(self):
        super().__init__()

        # Set up Prometheus metric types
        self.prometheus_metrics = {
            "counters": ["files_received", "transactions"],
            "gauges": ["last_file_timestamp"],
        }

    @cached_property
    def _security_credentials(self) -> dict:
        config = self.get_soteria_config()
        return {c["credential_type"]: c["value"] for c in config.security_credentials["inbound"]["credentials"]}

    @cached_property
    def sftp_credentials(self) -> SFTPCredentials:
        compound_key = self._security_credentials["compound_key"]
        return SFTPCredentials(**{k: compound_key.get(k) for k in SFTPCredentials._fields})

    @cached_property
    def skey(self) -> t.Optional[str]:
        return self._security_credentials.get("bink_private_key")

    @cached_property
    def filesource(self) -> FileSourceBase:
        return SftpFileSource(
            self.sftp_credentials, self.skey, Path(self.fileagent_config.path), logger=self.log, provider_agent=self,
            archive_path="archive"
        )

    def help(self, session: db.Session) -> str:
        return inspect.cleandoc(
            f"""
            This is the Wasabi scheme transaction SFTP file import agent.

            It is currently set up to monitor {self.config.get("path", session=session)} on SFTP host
            {self.sftp_credentials.host}:{self.sftp_credentials.port} for files to import.
            """
        )

    def yield_transactions_data(self, data: bytes) -> t.Iterable[dict]:
        fd = io.StringIO(data.decode())
        reader = csv.DictReader(fd)
        for raw_data in reader:
            if raw_data["Card Type Name"] not in self.payment_provider_map:
                continue
            yield {k: v for k, v in raw_data.items()}

    def to_transaction_fields(self, data: dict) -> SchemeTransactionFields:
        return SchemeTransactionFields(
            payment_provider_slug=Wasabi.payment_provider_map[data["Card Type Name"]],
            transaction_date=self.get_transaction_date(data),
            has_time=True,
            spend_amount=to_pennies(data["Amount"]),
            spend_multiplier=100,
            spend_currency="GBP",
            auth_code=data["Auth_code"],
            first_six=data["Card Number"][:6],
            last_four=data["Card Number"][-4:],
            extra_fields={},
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        """
        For Wasabi we need to take the Receipt No as this is the unique field, rather than Transaction No
        """
        return data["Receipt No_"]

    def get_mids(self, data: dict) -> t.List[str]:
        return [data["EFT Merchant No_"]]

    def get_transaction_date(self, data: dict) -> pendulum.DateTime:
        transaction_date_time = f"{data['Date']} {data['Time']}"
        transaction_date = pendulum.from_format(transaction_date_time, TXN_DATETIME_FORMAT, tz="Europe/London")
        return transaction_date
