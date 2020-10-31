import factory
from app.exports.models import ExportTransaction, FileSequenceNumber, PendingExport
from harness.factories.common import fake, generic, session


class ExportTransactionFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = ExportTransaction
        sqlalchemy_session = session
        sqlalchemy_session_persistence = "commit"

    transaction_id = generic.text.random.randstr(unique=True, length=50)
    provider_slug = generic.text.random.randstr(length=50)
    destination = generic.text.random.randstr(length=500)
    data = fake("json", num_rows=5)


class PendingExportFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = PendingExport
        sqlalchemy_session = session
        sqlalchemy_session_persistence = "commit"

    provider_slug = generic.text.random.randstr(length=50)
    matched_transaction = factory.SubFactory("harness.factories.app.factories.MatchedTransactionFactory")
    matched_transaction_id = factory.SelfAttribute("matched_transaction.id")


class FileSequenceNumberFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = FileSequenceNumber
        sqlalchemy_session = session
        sqlalchemy_session_persistence = "commit"

    provider_slug = generic.text.random.randstr(length=50)
    next_value = generic.numbers.integer_number(start=1)
