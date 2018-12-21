import typing as t
from datetime import datetime

from marshmallow import Schema, fields

from app import models
from app.config import KEY_PREFIX, ConfigValue
from app.imports.agents.bases.directory_watch_agent import DirectoryWatchAgent

WATCH_DIRECTORY_KEY = f"{KEY_PREFIX}imports.agents.testdir.watch_directory"

PROVIDER_SLUG = "testdir"


class TestDirAgentTransactionSchema(Schema):
    transuid = fields.String(required=True)
    merchno = fields.String(required=True)
    timestamp = fields.Integer(required=True)
    spend = fields.Integer(required=True)
    currency_code = fields.String(required=True)

    @staticmethod
    def to_queue_transaction(data: dict) -> models.SchemeTransaction:
        return models.SchemeTransaction(
            provider_slug=PROVIDER_SLUG,
            mid=data["merchno"],
            transaction_id=data["transuid"],
            transaction_date=datetime.fromtimestamp(data["timestamp"]),
            spend_amount=data["spend"],
            spend_multiplier=100,
            spend_currency=data["currency_code"].upper(),
            points_amount=None,
            points_multiplier=None,
            extra_fields={},
        )

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["transuid"]


class TestDirAgent(DirectoryWatchAgent):
    schema_class = TestDirAgentTransactionSchema
    provider_slug = PROVIDER_SLUG

    class Config:
        watch_directory = ConfigValue(WATCH_DIRECTORY_KEY, default="./itx")

    def yield_transactions_data(self, fd: t.IO[bytes]) -> t.Iterable[dict]:
        def warn(line, ex):
            MAX_LEN = 12
            if len(line) > MAX_LEN:
                overlap = len(line) - MAX_LEN
                line = f"{line[:MAX_LEN]} [+{overlap} chars]"
            self.log.warning(f"Invalid line in file: `{line}` ({repr(ex)}). Skipping.")

        for line in fd:
            try:
                mapping = {
                    k.strip(): v.strip()
                    for k, v in [kv.split(b":") for kv in line.split(b"|")]
                }
            except Exception as ex:
                if self.debug:
                    raise
                else:
                    warn(line, ex)
                    continue

            yield mapping
