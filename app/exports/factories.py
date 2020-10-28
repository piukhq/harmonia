import json

import factory
from app.exports.models import ExportTransaction, FileSequenceNumber, PendingExport
from mimesis import Generic
from mimesis.providers.base import BaseProvider


class JSONProvider(BaseProvider):
    class Meta:
        name = "json_provider"

    @staticmethod
    def json():
        """
        Generate some random JSON, we don't care what's in it
        """
        data = {}
        for _ in range(5):
            data.update({generic.text.random.randstr(unique=True, length=10): generic.text.random.randstr(length=50)})

        return json.dumps(data)


generic = Generic('en-gb')
generic.add_provider(JSONProvider)


class ExportTransactionFactory(factory.Factory):
    class Meta:
        model = ExportTransaction

    matched_transaction_id = factory.SubFactory("app.factories.MatchedTransactionFactory")
    transaction_id = generic.text.random.randstr(unique=True, length=50)
    provider_slug = generic.text.random.randstr(length=50)
    destination = generic.text.random.randstr(length=500)
    data = generic.json_provider.json()


class PendingExportFactory(factory.Factory):
    class Meta:
        model = PendingExport

    provider_slug = generic.text.random.randstr(length=50)
    matched_transaction_id = factory.SubFactory("app.factories.MatchedTransactionFactory")


class FileSequenceNumberFactory(factory.Factory):
    class Meta:
        model = FileSequenceNumber

    provider_slug = generic.text.random.randstr(length=50)
    next_value = generic.numbers.integer_number(start=1)
