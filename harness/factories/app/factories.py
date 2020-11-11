import factory
from app import models
from harness.factories.common import generic, session


class MatchedTransactionFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.MatchedTransaction
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    def merchant_identifier():
        yield from session.query(models.MerchantIdentifier).all()

    def payment_transaction():
        yield from session.query(models.PaymentTransaction).all()

    def scheme_transaction():
        yield from session.query(models.SchemeTransaction).all()

    merchant_identifier = factory.iterator(merchant_identifier)
    transaction_id = factory.LazyAttribute(lambda o: generic.text.random.randstr(unique=True, length=100))
    transaction_date = factory.LazyAttribute(lambda o: generic.datetime.formatted_datetime(fmt="%Y-%m-%d %H:%M:%S"))
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
        yield from session.query(models.LoyaltyScheme).all()

    def payment_provider():
        yield from session.query(models.PaymentProvider).all()

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
    transaction_date = factory.LazyAttribute(lambda o: generic.datetime.formatted_datetime(fmt="%Y-%m-%d %H:%M:%S"))
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

    def user_identity():
        yield from session.query(models.UserIdentity).all()

    merchant_identifier_ids = factory.LazyAttribute(lambda o: generic.numbers.random.randints(amount=5, a=1, b=1000000))
    provider_slug = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    transaction_id = factory.LazyAttribute(lambda o: generic.text.random.randstr(unique=True, length=100))
    settlement_key = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=100))
    transaction_date = factory.LazyAttribute(lambda o: generic.datetime.formatted_datetime(fmt="%Y-%m-%d %H:%M:%S"))
    has_time = factory.LazyAttribute(lambda o: generic.development.boolean())
    spend_amount = factory.LazyAttribute(lambda o: generic.numbers.integer_number(start=1))
    spend_multiplier = factory.LazyAttribute(lambda o: generic.numbers.integer_number(start=1))
    spend_currency = factory.LazyAttribute(lambda o: generic.business.currency_iso_code(allow_random=True))
    card_token = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=100))
    status = factory.LazyAttribute(lambda o: generic.choice(items=[x for x in models.TransactionStatus]))
    auth_code = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=20))
    user_identity = factory.iterator(user_identity)
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
