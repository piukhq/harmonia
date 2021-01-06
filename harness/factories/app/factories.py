import factory
from app import models
from harness.factories.common import generic, session


# Pre-fetch user_identity_ids for the PaymentTransactionFactory. At least one user_identity record will need to exist
# but this seems fair as it is a foreign key for payment_transaction.user_identity_id
user_identity_ids = [x.id for x in session.query(models.UserIdentity).limit(50).all()]


class MatchedTransactionFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.MatchedTransaction
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    def merchant_identifier():
        yield from session.query(models.MerchantIdentifier).limit(500).all()

    def payment_transaction():
        yield from session.query(models.PaymentTransaction).limit(500).all()

    def scheme_transaction():
        yield from session.query(models.SchemeTransaction).limit(500).all()

    merchant_identifier = factory.iterator(merchant_identifier)
    transaction_id = factory.LazyAttribute(lambda o: generic.text.random.randstr(unique=True, length=100))
    transaction_date = factory.LazyAttribute(lambda o: generic.transaction_date_provider.transaction_date(days=30))
    spend_amount = factory.LazyAttribute(lambda o: generic.numbers.integer_number(start=1))
    spend_multiplier = factory.LazyAttribute(lambda o: generic.numbers.integer_number(start=1))
    spend_currency = factory.LazyAttribute(lambda o: generic.business.currency_iso_code(allow_random=True))
    card_token = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=100))
    matching_type = factory.LazyAttribute(lambda o: generic.choice(items=[x for x in models.MatchingType]))
    status = factory.LazyAttribute(lambda o: generic.choice(items=[x for x in models.MatchedTransactionStatus]))
    payment_transaction = factory.iterator(payment_transaction)
    scheme_transaction = factory.iterator(scheme_transaction)
    extra_fields = factory.LazyAttribute(lambda o: generic.json_provider.json())


class MerchantIdentifierFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.MerchantIdentifier
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    def loyalty_scheme():
        yield from session.query(models.LoyaltyScheme).limit(500).all()

    def payment_provider():
        yield from session.query(models.PaymentProvider).limit(500).all()

    mid = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    store_id = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    loyalty_scheme = factory.iterator(loyalty_scheme)
    payment_provider = factory.iterator(payment_provider)
    location = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=250))
    postcode = factory.LazyAttribute(lambda o: generic.address.zip_code())


class LoyaltySchemeFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.LoyaltyScheme
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    slug = factory.LazyAttribute(lambda o: generic.text.random.randstr(unique=True, length=50))


class PaymentProviderFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.PaymentProvider
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    slug = factory.LazyAttribute(lambda o: generic.text.random.randstr(unique=True, length=50))


class SchemeTransactionFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.SchemeTransaction
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    merchant_identifier_ids = factory.LazyAttribute(lambda o: generic.numbers.random.randints(amount=5, a=1, b=1000000))
    provider_slug = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    payment_provider_slug = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    transaction_id = factory.LazyAttribute(lambda o: generic.text.random.randstr(unique=True, length=50))
    transaction_date = factory.LazyAttribute(lambda o: generic.transaction_date_provider.transaction_date(days=30))
    has_time = factory.LazyAttribute(lambda o: generic.development.boolean())
    spend_amount = factory.LazyAttribute(lambda o: generic.numbers.integer_number(start=1))
    spend_multiplier = factory.LazyAttribute(lambda o: generic.numbers.integer_number(start=1))
    spend_currency = factory.LazyAttribute(lambda o: generic.business.currency_iso_code(allow_random=True))
    status = factory.LazyAttribute(lambda o: generic.choice(items=[x for x in models.TransactionStatus]))
    auth_code = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=20))
    match_group = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=36))
    extra_fields = factory.LazyAttribute(lambda o: generic.json_provider.json())


class PaymentTransactionFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.PaymentTransaction
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    merchant_identifier_ids = factory.LazyAttribute(lambda o: generic.numbers.random.randints(amount=5, a=1, b=1000000))
    provider_slug = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    transaction_id = factory.LazyAttribute(lambda o: generic.text.random.randstr(unique=True, length=100))
    settlement_key = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=100))
    transaction_date = factory.LazyAttribute(lambda o: generic.transaction_date_provider.transaction_date(days=30))
    has_time = factory.LazyAttribute(lambda o: generic.development.boolean())
    spend_amount = factory.LazyAttribute(lambda o: generic.numbers.integer_number(start=1))
    spend_multiplier = factory.LazyAttribute(lambda o: generic.numbers.integer_number(start=1))
    spend_currency = factory.LazyAttribute(lambda o: generic.business.currency_iso_code(allow_random=True))
    card_token = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=100))
    status = factory.LazyAttribute(lambda o: generic.choice(items=[x for x in models.TransactionStatus]))
    auth_code = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=20))
    # We can't pass in user_identity as generated list of related records, as we do for the other factories, as
    # the relationship has been setup as a back_populates one for payment_transactions and to do so would result
    # in many SELECT statements
    user_identity_id = factory.LazyAttribute(lambda o: generic.choice(items=user_identity_ids))
    match_group = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=36))
    extra_fields = factory.LazyAttribute(lambda o: generic.json_provider.json())


class UserIdentityFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.UserIdentity
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    loyalty_id = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=250))
    scheme_account_id = factory.LazyAttribute(lambda o: generic.numbers.integer_number(start=1))
    user_id = factory.LazyAttribute(lambda o: generic.numbers.integer_number(start=1))
    credentials = factory.LazyAttribute(lambda o: generic.cryptographic.token_urlsafe())
    first_six = factory.LazyAttribute(lambda o: generic.random.generate_string("0123456789", length=6))
    last_four = factory.LazyAttribute(lambda o: generic.random.generate_string("0123456789", length=4))
