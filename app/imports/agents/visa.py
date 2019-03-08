import typing as t
import inspect
import logging

import gnupg
import pendulum

from app.config import KEY_PREFIX, ConfigValue
from app.feeds import ImportFeedTypes
from app.imports.agents.bases.file_agent import FileAgent
from app import models

PROVIDER_SLUG = "visa"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"

DATE_FORMAT = "YYYYMMDD"


logging.getLogger("gnupg").setLevel(logging.INFO)


class VisaAgent(FileAgent):
    feed_type = ImportFeedTypes.PAYMENT
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
        "purchase_date": lambda x: pendulum.from_format(x, DATE_FORMAT),
        "transaction_date": lambda x: pendulum.from_format(x, DATE_FORMAT),
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

    def yield_transactions_data(self, fd: t.IO) -> t.Iterable[dict]:
        gpg = gnupg.GPG(gnupghome="keyring")
        result = gpg.decrypt_file(fd)
        if not result.ok:
            raise self.ImportError(f"Failed to decrypt file {fd.name}: {result.status}")
        lines = str(result).split("\n")
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
    def to_queue_transaction(
        data: dict, merchant_identifier_ids: t.List[int], transaction_id: str
    ) -> models.PaymentTransaction:
        return models.PaymentTransaction(
            merchant_identifier_ids=merchant_identifier_ids,
            transaction_id=transaction_id,
            transaction_date=data["transaction_date"],
            spend_amount=data["transaction_amount"],
            spend_multiplier=100,
            spend_currency=data["country_currency_code"],
            card_token=data["external_card_holder_id"],
            extra_fields={k: data[k] for k in ("merchant_description_name", "merchant_city")},
        )
