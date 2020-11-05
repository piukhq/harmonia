import factory
from app import models
from app.exports.models import ExportTransaction, FileSequenceNumber, PendingExport
from harness.factories.common import fake, session


class ExportTransactionFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = ExportTransaction
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    transaction_id = fake("uuid4")
    provider_slug = fake("pystr", min_chars=5, max_chars=50)
    destination = fake("pystr", min_chars=10, max_chars=500)
    data = fake("json", num_rows=5)


class PendingExportFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = PendingExport
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    provider_slug = fake("pystr", min_chars=5, max_chars=50)

    def matched_transaction():
        yield from session.query(models.MatchedTransaction).all()

    matched_transaction = factory.iterator(matched_transaction)


class FileSequenceNumberFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = FileSequenceNumber
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    provider_slug = fake("pystr", min_chars=5, max_chars=50)
    next_value = fake("random_int", min=1, max=999999, step=1)
