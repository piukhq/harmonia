import typing as t

import pendulum

from app import models
from app.config import KEY_PREFIX, ConfigValue
from app.feeds import ImportFeedTypes
from app.imports.agents.bases.directory_watch_agent import DirectoryWatchAgent
from app.utils import file_split

PROVIDER_SLUG = "example-payment-provider"
WATCH_DIRECTORY_KEY = (
    f"{KEY_PREFIX}imports.agents.example-payment-provider.watch_directory"
)


class ExamplePaymentProviderAgent(DirectoryWatchAgent):
    feed_type = ImportFeedTypes.PAYMENT
    provider_slug = PROVIDER_SLUG

    file_fields = ["mid", "transaction_id", "date", "spend", "token"]
    field_transforms: t.Dict[str, t.Callable] = {"date": pendulum.parse, "spend": int}

    class Config:
        watch_directory = ConfigValue(
            WATCH_DIRECTORY_KEY, default="files/imports/example-payment-provider"
        )

    def yield_transactions_data(self, fd: t.IO) -> t.Iterable[dict]:
        for record in file_split(fd, sep="\x1e"):
            raw_data = dict(zip(self.file_fields, record.split("\x1f")))
            yield {k: self.field_transforms.get(k, str)(v) for k, v in raw_data.items()}

    @staticmethod
    def to_queue_transaction(
        data: dict, merchant_identifier_id: int, transaction_id: str
    ) -> models.PaymentTransaction:
        return models.PaymentTransaction(
            merchant_identifier_id=merchant_identifier_id,
            transaction_id=transaction_id,
            transaction_date=data["date"],
            spend_amount=data["spend"],
            spend_multiplier=100,
            spend_currency="GBP",
            card_token=data["token"],
            extra_fields={},
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["transaction_id"]

    @staticmethod
    def get_mid(data: dict) -> str:
        return data["mid"]
