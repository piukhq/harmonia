import factory
from app.imports.models import ImportTransaction
from harness.factories.common import generic


class ImportTransactionFactory(factory.Factory):
    class Meta:
        model = ImportTransaction

    transaction_id = generic.text.random.randstr(unique=True, length=50)
    provider_slug = generic.text.random.randstr(length=50)
    identified = generic.development.boolean()
    match_group = generic.text.random.randstr(length=36)
    source = generic.text.random.randstr(length=500)
    data = generic.json_provider.json()
