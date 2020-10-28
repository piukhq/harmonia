import json

import factory
from app.imports.models import ImportTransaction
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


class ImportTransactionFactory(factory.Factory):
    class Meta:
        model = ImportTransaction

    transaction_id = generic.text.random.randstr(unique=True, length=50)
    provider_slug = generic.text.random.randstr(length=50)
    identified = generic.development.boolean()
    match_group = generic.text.random.randstr(length=36)
    source = generic.text.random.randstr(length=500)
    data = generic.json_provider.json()
