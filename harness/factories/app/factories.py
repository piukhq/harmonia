import factory
from app import models
from harness.factories.common import fake, generic, session


class MatchedTransactionFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.MatchedTransaction
        sqlalchemy_session = session
        sqlalchemy_session_persistence = "commit"

    merchant_identifier_id = factory.SelfAttribute("merchant_identifier.id")
    merchant_identifier = factory.SubFactory("harness.factories.app.factories.MerchantIdentifierFactory")
    transaction_id = generic.text.random.randstr(unique=True, length=100)
    transaction_date = generic.datetime.formatted_datetime(fmt="%Y-%m-%d %H:%M:%S")
    spend_amount = generic.numbers.integer_number(start=1)
    spend_multiplier = generic.numbers.integer_number(start=1)
    spend_currency = generic.business.currency_iso_code(allow_random=True)
    card_token = generic.text.random.randstr(length=100)
    matching_type = generic.choice(items=[x.value for x in models.MatchingType])
    status = generic.choice(items=[x.value for x in models.MatchedTransactionStatus])
    payment_transaction_id = factory.SelfAttribute("payment_transaction.id")
    payment_transaction = factory.SubFactory("harness.factories.app.factories.PaymentTransactionFactory")
    scheme_transaction_id = factory.SelfAttribute("scheme_transaction.id")
    scheme_transaction = factory.SubFactory("harness.factories.app.factories.SchemeTransactionFactory")
    extra_fields = generic.json_provider.json()

    # pending_exports = factory.RelatedFactoryList(
    #     "harness.factories.exports.factories.PendingExportFactory", "matched_transaction", size=3
    # )


class MerchantIdentifierFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.MerchantIdentifier
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    def loyalty_scheme():
        yield from session.query(models.LoyaltyScheme).all()

    def payment_provider():
        yield from session.query(models.PaymentProvider).all()

    mid = fake("uuid4")
    store_id = fake("uuid4")
    loyalty_scheme = factory.iterator(loyalty_scheme)
    payment_provider = factory.iterator(payment_provider)
    location = fake("pystr", min_chars=10, max_chars=250)
    postcode = fake("postcode", locale="en-GB")

    # matched_transactions = factory.RelatedFactoryList(MatchedTransactionFactory, "merchant_identifier", size=3)


class LoyaltySchemeFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.LoyaltyScheme
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    slug = fake("uuid4")

    # merchant_identifiers = factory.RelatedFactoryList(MerchantIdentifierFactory, "loyalty_scheme", size=3)


class PaymentProviderFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.PaymentProvider
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    slug = fake("uuid4")

    # merchant_identifiers = factory.RelatedFactoryList(MerchantIdentifierFactory, "payment_provider", size=3)


class SchemeTransactionFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.SchemeTransaction
        sqlalchemy_session = session
        sqlalchemy_session_persistence = "commit"

    merchant_identifier_ids = generic.numbers.random.randints(amount=5, a=1, b=1000000)
    provider_slug = generic.text.random.randstr(length=50)
    payment_provider_slug = generic.text.random.randstr(length=50)
    transaction_id = generic.text.random.randstr(unique=True, length=50)
    transaction_date = generic.datetime.formatted_datetime(fmt="%Y-%m-%d %H:%M:%S")
    has_time = generic.development.boolean()
    spend_amount = generic.numbers.integer_number(start=1)
    spend_multiplier = generic.numbers.integer_number(start=1)
    spend_currency = generic.business.currency_iso_code(allow_random=True)
    status = generic.choice(items=[x.value for x in models.TransactionStatus])
    auth_code = generic.text.random.randstr(length=20)
    match_group = generic.text.random.randstr(length=36)
    extra_fields = generic.json_provider.json()

    # matched_transactions = factory.RelatedFactoryList(MatchedTransactionFactory, "scheme_transaction", size=3)


class PaymentTransactionFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.PaymentTransaction
        sqlalchemy_session = session
        sqlalchemy_session_persistence = "commit"

    merchant_identifier_ids = generic.numbers.random.randints(amount=5, a=1, b=1000000)
    provider_slug = generic.text.random.randstr(length=50)
    transaction_id = generic.text.random.randstr(unique=True, length=100)
    settlement_key = generic.text.random.randstr(length=100)
    transaction_date = generic.datetime.formatted_datetime(fmt="%Y-%m-%d %H:%M:%S")
    has_time = generic.development.boolean()
    spend_amount = generic.numbers.integer_number(start=1)
    spend_multiplier = generic.numbers.integer_number(start=1)
    spend_currency = generic.business.currency_iso_code(allow_random=True)
    card_token = generic.text.random.randstr(length=100)
    status = generic.choice(items=[x.value for x in models.TransactionStatus])
    auth_code = generic.text.random.randstr(length=20)
    user_identity_id = factory.SelfAttribute("user_identity.id")
    user_identity = factory.SubFactory("harness.factories.app.factories.UserIdentityFactory")
    match_group = generic.text.random.randstr(length=36)
    extra_fields = generic.json_provider.json()

    # matched_transactions = factory.RelatedFactoryList(MatchedTransactionFactory, "payment_transaction", size=3)


class UserIdentityFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.UserIdentity
        sqlalchemy_session = session
        sqlalchemy_session_persistence = None

    loyalty_id = fake("pystr", min_chars=10, max_chars=250)
    scheme_account_id = fake("random_int", min=1, max=999999, step=1)
    user_id = fake("random_int", min=1, max=999999, step=1)
    credentials = fake("uuid4")
    first_six = fake("pystr_format", string_format="######", letters="0123456789")
    last_four = fake("pystr_format", string_format="####", letters="0123456789")

    # payment_transaction = factory.RelatedFactoryList(PaymentTransactionFactory, "user_identity", size=3)
