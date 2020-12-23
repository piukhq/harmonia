import factory
from app import models
from app.exports.models import ExportTransaction, FileSequenceNumber, PendingExport
from harness.factories.common import generic, session


class ExportTransactionFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = ExportTransaction
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    transaction_id = factory.LazyAttribute(lambda o: generic.text.random.randstr(unique=True, length=50))
    provider_slug = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    destination = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=500))
    data = factory.LazyAttribute(lambda o: generic.json_provider.json())


class PendingExportFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = PendingExport
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    def matched_transaction():
        yield from session.query(models.MatchedTransaction).limit(500).all()

    provider_slug = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    matched_transaction = factory.iterator(matched_transaction)


class FileSequenceNumberFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = FileSequenceNumber
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    provider_slug = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    next_value = factory.LazyAttribute(lambda o: generic.numbers.integer_number(start=1))
