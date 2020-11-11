import factory
from app.imports.models import ImportTransaction
from harness.factories.common import fake, generic, session


class ImportTransactionFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = ImportTransaction
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    # transaction_id = fake("uuid4")
    # # provider_slug = fake("pystr", min_chars=5, max_chars=50)
    # provider_slug = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    # identified = fake("boolean", chance_of_getting_true=50)
    # match_group = fake("pystr", min_chars=5, max_chars=36)
    # source = fake("pystr", min_chars=50, max_chars=500)
    # data = fake("json", num_rows=5)

    transaction_id = factory.LazyAttribute(lambda o: generic.text.random.randstr(unique=True, length=50))
    provider_slug = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    identified = factory.LazyAttribute(lambda o: generic.development.boolean())
    match_group = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=36))
    source = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=500))
    data = factory.LazyAttribute(lambda o: generic.json_provider.json())

