from datetime import datetime
import typing as t

from marshmallow import Schema, fields

from app.imports.agents.bases.directory_watch_agent import DirectoryWatchAgent, log
from app.config import ConfigValue, KEY_PREFIX
from app import models

WATCH_DIRECTORY_KEY = f"{KEY_PREFIX}imports.agents.testdir.watch_directory"

PROVIDER_SLUG = 'testdir'


class TestDirAgentTransactionSchema(Schema):
    transuid = fields.String(required=True)
    merchno = fields.String(required=True)
    timestamp = fields.Integer(required=True)
    spend = fields.Decimal(required=True)
    currency_code = fields.String(required=True)

    @staticmethod
    def to_scheme_transaction(data: t.Dict[str, t.Any]) -> models.SchemeTransaction:
        return models.SchemeTransaction(
            provider_slug=PROVIDER_SLUG,
            mid=data['merchno'],
            transaction_id=data['transuid'],
            transaction_date=datetime.fromtimestamp(data['timestamp']),
            spend_amount=data['spend'] * 100,
            spend_multiplier=100,
            spend_currency=data['currency_code'].upper(),
            points_amount=None,
            points_multiplier=None,
            extra_fields={})

    @staticmethod
    def get_transaction_id(data: t.Dict[str, t.Any]) -> str:
        return data['transuid']


class TestDirAgent(DirectoryWatchAgent):
    schema_class = TestDirAgentTransactionSchema
    provider_slug = PROVIDER_SLUG

    class Config:
        watch_directory = ConfigValue(WATCH_DIRECTORY_KEY, default='./itx')

    def yield_transactions_data(self, fd: t.TextIO) -> t.Iterable[t.Dict[str, t.Any]]:
        def warn(line, ex):
            MAX_LEN = 12
            if len(line) > MAX_LEN:
                overlap = len(line) - MAX_LEN
                line = f"{line[:MAX_LEN]} [+{overlap} chars]"
            log.warning(f"Invalid line in file: `{line}` ({repr(ex)}). Skipping.")

        for line in fd:
            try:
                mapping = {k.strip(): v.strip() for k, v in [kv.split(':') for kv in line.split('|')]}
            except Exception as ex:
                warn(line, ex)
                continue

            yield mapping
