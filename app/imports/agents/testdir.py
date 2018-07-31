import typing as t
import json

from marshmallow import Schema, fields

from app.imports.agents.bases.directory_watch_agent import DirectoryWatchAgent, log
from app.config import ConfigValue, KEY_PREFIX
from app import models


WATCH_DIRECTORY = f"{KEY_PREFIX}imports.agents.testdir.watch_directory"


class TestDirAgentTransactionSchema(Schema):
    tid = fields.String()
    value = fields.Integer()
    card = fields.String()

    @staticmethod
    def to_scheme_transaction(data: t.Dict[str, t.Any]) -> models.SchemeTransaction:
        return models.SchemeTransaction(
            transaction_id=data['tid'],
            pence=data['value'],
            points_earned=None,
            card_id=data['card'],
            total_points=None)

    @staticmethod
    def get_transaction_id(data: t.Dict[str, t.Any]) -> str:
        return data['tid']


class TestDirAgent(DirectoryWatchAgent):
    schema_class = TestDirAgentTransactionSchema
    provider_slug = 'testdir'

    class Config:
        watch_directory = ConfigValue(WATCH_DIRECTORY, default='./testdir')

    def yield_transactions_data(self, fd: t.TextIO) -> t.Iterable[models.SchemeTransaction]:
        def warn(line, ex):
            MAX_LEN = 12
            if len(line) > MAX_LEN:
                overlap = len(line) - MAX_LEN
                line = f"{line[:MAX_LEN]} [+{overlap} chars]"
            log.warning(f"Invalid line in file: `{line}` ({repr(ex)}). Skipping.")

        for line in fd:
            try:
                data = json.loads(line)
            except json.decoder.JSONDecodeError as ex:
                warn(line, ex)
                continue

            yield data
