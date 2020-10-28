import factory
from app.exports.models import ExportTransaction, FileSequenceNumber, PendingExport
from harness.factories.common import generic


class ExportTransactionFactory(factory.Factory):
    class Meta:
        model = ExportTransaction

    matched_transaction = factory.SubFactory("harness.factories.app.factories.MatchedTransactionFactory")
    matched_transaction_id = factory.SelfAttribute("matched_transaction.id")
    transaction_id = generic.text.random.randstr(unique=True, length=50)
    provider_slug = generic.text.random.randstr(length=50)
    destination = generic.text.random.randstr(length=500)
    data = generic.json_provider.json()


class PendingExportFactory(factory.Factory):
    class Meta:
        model = PendingExport

    provider_slug = generic.text.random.randstr(length=50)
    matched_transaction = factory.SubFactory("harness.factories.app.factories.MatchedTransactionFactory")
    matched_transaction_id = factory.SelfAttribute("matched_transaction.id")


class FileSequenceNumberFactory(factory.Factory):
    class Meta:
        model = FileSequenceNumber

    provider_slug = generic.text.random.randstr(length=50)
    next_value = generic.numbers.integer_number(start=1)
