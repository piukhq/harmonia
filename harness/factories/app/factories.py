import factory

from app import models
from harness.factories.common import generic, session


class MatchedTransactionFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.MatchedTransaction
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    def merchant_identifier():
        yield from session.query(models.MerchantIdentifier).limit(500).all()

    merchant_identifier = factory.iterator(merchant_identifier)
    mid = factory.LazyAttribute(lambda o: generic.text.random.randstr(unique=True, length=50))
    transaction_id = factory.LazyAttribute(lambda o: generic.text.random.randstr(unique=True, length=100))
    transaction_date = factory.LazyAttribute(lambda o: generic.transaction_date_provider.transaction_date(days=30))
    spend_amount = factory.LazyAttribute(lambda o: generic.numeric.integer_number(start=1))
    spend_multiplier = factory.LazyAttribute(lambda o: generic.numeric.integer_number(start=1))
    spend_currency = factory.LazyAttribute(lambda o: generic.finance.currency_iso_code(allow_random=True))
    card_token = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=100))
    matching_type = factory.LazyAttribute(lambda o: generic.choice(items=[x for x in models.MatchingType]))
    status = factory.LazyAttribute(lambda o: generic.choice(items=[x for x in models.MatchedTransactionStatus]))
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

    identifier = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    identifier_type = factory.LazyAttribute(lambda o: generic.choice(items=[x for x in models.IdentifierType]))
    location_id = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
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


class TransactionFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.Transaction
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    feed_type = factory.LazyAttribute(lambda o: generic.choice(items=[x for x in models.FeedType]))
    status = factory.LazyAttribute(lambda o: generic.choice(items=[x for x in models.TransactionStatus]))
    merchant_identifier_ids = factory.LazyAttribute(lambda o: generic.numeric.random.randints(amount=5, a=1, b=1000000))
    mids = factory.LazyAttribute(lambda o: [generic.text.random.randstr(length=50)])
    merchant_slug = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    payment_provider_slug = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    transaction_id = factory.LazyAttribute(lambda o: generic.text.random.randstr(unique=True, length=50))
    match_group = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=36))
    transaction_date = factory.LazyAttribute(lambda o: generic.transaction_date_provider.transaction_date(days=30))
    has_time = factory.LazyAttribute(lambda o: generic.development.boolean())
    spend_amount = factory.LazyAttribute(lambda o: generic.numeric.integer_number(start=1))
    spend_multiplier = factory.LazyAttribute(lambda o: generic.numeric.integer_number(start=1))
    spend_currency = factory.LazyAttribute(lambda o: generic.finance.currency_iso_code(allow_random=True))
    auth_code = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=20))
    approval_code = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=20))


class SchemeTransactionFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.SchemeTransaction
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    merchant_identifier_ids = factory.LazyAttribute(lambda o: generic.numeric.random.randints(amount=5, a=1, b=1000000))
    mids = factory.LazyAttribute(lambda o: [generic.text.random.randstr(length=50)])
    provider_slug = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    payment_provider_slug = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    transaction_id = factory.LazyAttribute(lambda o: generic.text.random.randstr(unique=True, length=50))
    transaction_date = factory.LazyAttribute(lambda o: generic.transaction_date_provider.transaction_date(days=30))
    has_time = factory.LazyAttribute(lambda o: generic.development.boolean())
    spend_amount = factory.LazyAttribute(lambda o: generic.numeric.integer_number(start=1))
    spend_multiplier = factory.LazyAttribute(lambda o: generic.numeric.integer_number(start=1))
    spend_currency = factory.LazyAttribute(lambda o: generic.finance.currency_iso_code(allow_random=True))
    status = factory.LazyAttribute(lambda o: generic.choice(items=[x for x in models.TransactionStatus]))
    auth_code = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=20))
    match_group = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=36))
    extra_fields = factory.LazyAttribute(lambda o: generic.json_provider.json())


class PaymentTransactionFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.PaymentTransaction
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    merchant_identifier_ids = factory.LazyAttribute(lambda o: generic.numeric.random.randints(amount=5, a=1, b=1000000))
    mid = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    provider_slug = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=50))
    transaction_id = factory.LazyAttribute(lambda o: generic.text.random.randstr(unique=True, length=100))
    settlement_key = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=100))
    transaction_date = factory.LazyAttribute(lambda o: generic.transaction_date_provider.transaction_date(days=30))
    has_time = factory.LazyAttribute(lambda o: generic.development.boolean())
    spend_amount = factory.LazyAttribute(lambda o: generic.numeric.integer_number(start=1))
    spend_multiplier = factory.LazyAttribute(lambda o: generic.numeric.integer_number(start=1))
    spend_currency = factory.LazyAttribute(lambda o: generic.finance.currency_iso_code(allow_random=True))
    card_token = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=100))
    status = factory.LazyAttribute(lambda o: generic.choice(items=[x for x in models.TransactionStatus]))
    auth_code = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=20))
    match_group = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=36))
    extra_fields = factory.LazyAttribute(lambda o: generic.json_provider.json())


class UserIdentityFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.UserIdentity
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    transaction_id = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=100))
    loyalty_id = factory.LazyAttribute(lambda o: generic.text.random.randstr(length=250))
    scheme_account_id = factory.LazyAttribute(lambda o: generic.numeric.integer_number(start=1))
    user_id = factory.LazyAttribute(lambda o: generic.numeric.integer_number(start=1))
    credentials = factory.LazyAttribute(lambda o: generic.cryptographic.token_urlsafe())
    first_six = factory.LazyAttribute(lambda o: generic.random.generate_string("0123456789", length=6))
    last_four = factory.LazyAttribute(lambda o: generic.random.generate_string("0123456789", length=4))
