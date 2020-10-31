import factory
from app.imports.models import ImportTransaction
from harness.factories.common import fake, generic, session


class ImportTransactionFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = ImportTransaction
        sqlalchemy_session = session
        sqlalchemy_session_persistence = "commit"

    transaction_id = generic.text.random.randstr(unique=True, length=50)
    provider_slug = generic.text.random.randstr(length=50)
    identified = generic.development.boolean()
    match_group = generic.text.random.randstr(length=36)
    source = generic.text.random.randstr(length=500)
    data = fake("json", num_rows=5)
