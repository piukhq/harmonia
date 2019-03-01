import typing as t

import pendulum

from app import models
from app.config import KEY_PREFIX, ConfigValue
from app.feeds import ImportFeedTypes
from app.imports.agents.bases.directory_watch_agent import DirectoryWatchAgent
from app.imports.agents.bases.blob_storage_agent import BlobStorageAgent
from app.utils import file_split
import settings

PROVIDER_SLUG = "example-loyalty-scheme"
WATCH_DIRECTORY_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.watch_directory"
BLOB_LEASE_DURATION_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.blob_lease_duration"
BLOB_PREFIX_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.blob_prefix"


class ExampleLoyaltySchemeAgentMixin:
    file_fields = ["mid", "transaction_id", "date", "spend", "points"]
    field_transforms: t.Dict[str, t.Callable] = {"date": pendulum.parse, "spend": int, "points": int}

    def yield_transactions_data(self, fd: t.IO[bytes]) -> t.Iterable[dict]:
        for record in file_split(fd, sep="\x1e"):
            raw_data = dict(zip(self.file_fields, record.split("\x1f")))
            yield {k: self.field_transforms.get(k, str)(v) for k, v in raw_data.items()}

    @staticmethod
    def to_queue_transaction(
        data: dict, merchant_identifier_ids: t.List[int], transaction_id: str
    ) -> models.SchemeTransaction:
        return models.SchemeTransaction(
            merchant_identifier_ids=merchant_identifier_ids,
            transaction_id=transaction_id,
            transaction_date=data["date"],
            spend_amount=data["spend"],
            spend_multiplier=100,
            spend_currency="GBP",
            points_amount=data["points"],
            points_multiplier=100,
            extra_fields={},
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["transaction_id"]

    @staticmethod
    def get_mids(data: dict) -> t.List[str]:
        return [data["mid"]]


class ExampleLoyaltySchemeAgent_BlobStorage(BlobStorageAgent, ExampleLoyaltySchemeAgentMixin):
    feed_type = ImportFeedTypes.SCHEME
    provider_slug = PROVIDER_SLUG

    class Config:
        blob_lease_duration = ConfigValue(BLOB_LEASE_DURATION_KEY, default="60")
        blob_prefix = ConfigValue(BLOB_PREFIX_KEY, default=f"{PROVIDER_SLUG}/")


class ExampleLoyaltySchemeAgent_DirectoryWatch(DirectoryWatchAgent, ExampleLoyaltySchemeAgentMixin):
    feed_type = ImportFeedTypes.SCHEME
    provider_slug = PROVIDER_SLUG

    class Config:
        watch_directory = ConfigValue(WATCH_DIRECTORY_KEY, default="files/imports/example-loyalty-scheme")


ExampleLoyaltySchemeAgent = (
    ExampleLoyaltySchemeAgent_BlobStorage if settings.USE_BLOB_STORAGE else ExampleLoyaltySchemeAgent_DirectoryWatch
)
