import factory

from app import models
from app.exports.models import ExportTransaction, FileSequenceNumber, PendingExport, ExportTransactionStatus
from harness.factories.common import generic, session


class ExportTransactionFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = ExportTransaction
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    transaction_id = factory.LazyAttribute(lambda o: generic.text.random.randstr(unique=True, length=50))
    provider_slug = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    transaction_date = factory.LazyAttribute(lambda o: generic.transaction_date_provider.transaction_date(days=30))
    spend_amount = factory.LazyAttribute(lambda o: generic.numeric.integer_number(start=1))
    spend_currency = factory.LazyAttribute(lambda o: generic.finance.currency_iso_code(allow_random=True))
    loyalty_id = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    mid = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    primary_identifier = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    user_id = factory.LazyAttribute(lambda o: generic.numeric.integer_number(start=1))
    scheme_account_id = factory.LazyAttribute(lambda o: generic.numeric.integer_number(start=1))
    credentials = factory.LazyAttribute(lambda o: generic.cryptographic.token_urlsafe())
    auth_code = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=20))
    approval_code = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=20))
    status = factory.LazyAttribute(lambda o: generic.choice(items=[x for x in ExportTransactionStatus]))


class PendingExportFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = PendingExport
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    def export_transaction():
        yield from session.query(models.ExportTransaction).limit(500).all()

    provider_slug = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    export_transaction = factory.iterator(export_transaction)
    retry_count = factory.LazyAttribute(lambda o: generic.numeric.integer_number(start=0, end=3))


class FileSequenceNumberFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = FileSequenceNumber
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    provider_slug = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    next_value = factory.LazyAttribute(lambda o: generic.numeric.integer_number(start=1))
