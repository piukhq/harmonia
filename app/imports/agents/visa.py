import typing as t
import inspect

from app.config import KEY_PREFIX, ConfigValue
from app.feeds import ImportFeedTypes
from app.imports.agents.bases.directory_watch_agent import DirectoryWatchAgent

PROVIDER_SLUG = "visa"
WATCH_DIRECTORY_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.watch_directory"

DATE_FORMAT = "YYYY-MM-DD"
DATETIME_FORMAT = "YYYY-MM-DD-HH.mm.ss"


class VisaAgent(DirectoryWatchAgent):
    feed_type = ImportFeedTypes.PAYMENT
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

    file_field_types = {"spend": int}

    class Config:
        watch_directory = ConfigValue(
            WATCH_DIRECTORY_KEY, default=f"files/imports/{PROVIDER_SLUG}"
        )

    def yield_transactions_data(self, fd: t.IO) -> t.Iterable[dict]:
        for line in fd.readlines():
            raw_data = [l.strip() for l in line.split("|")]

            if not raw_data or raw_data[0] != "D":
                continue

            yield {
                k: self.file_field_types.get(k, str)(v)
                for k, v in zip(self.file_fields, raw_data)
            }

    def help(self) -> str:
        return inspect.cleandoc(
            f"""
        This is the Visa payment transaction file import agent.

        It is currently set up to monitor {self.Config.watch_directory} for files to import.
        """
        )
