import json

import factory
from app import models
from mimesis import Generic
from mimesis.providers.base import BaseProvider


class JSONProvider(BaseProvider):
    class Meta:
        name = "json_provider"

    @staticmethod
    def json():
        """
        Generate some random JSON, we don't care what's in it
        """
        data = {}
        for _ in range(5):
            data.update({generic.text.random.randstr(unique=True, length=10): generic.text.random.randstr(length=50)})

        return json.dumps(data)


generic = Generic("en-gb")
generic.add_provider(JSONProvider)


# One side
class LoyaltySchemeFactory(factory.Factory):
    class Meta:
        model = models.LoyaltyScheme

    slug = generic.text.random.randstr(unique=True, length=50)
    merchant_identifiers = factory.RelatedFactoryList("app.factories.MerchantIdentifier", "loyalty_scheme", size=3)
    # merchant_identifiers = s.orm.relationship("MerchantIdentifier", backref="loyalty_scheme")


class PaymentProviderFactory(factory.Factory):
    class Meta:
        model = models.PaymentProvider

    slug = generic.text.random.randstr(unique=True, length=50)
    merchant_identifiers = factory.RelatedFactoryList("app.factories.MerchantIdentifier", "payment_provider", size=3)


# Many side
class MerchantIdentifierFactory(factory.Factory):
    class Meta:
        model = models.MerchantIdentifier

    mid = generic.text.random.randstr(length=50)
    store_id = generic.text.random.randstr(length=50)
    # loyalty_scheme_id = s.Column(s.Integer, s.ForeignKey("loyalty_scheme.id"))
    loyalty_scheme_id = factory.SelfAttribute("loyalty_scheme.id")
    loyalty_scheme = factory.SubFactory("app.factories.LoyaltySchemeFactory", merchant_identifiers=[])
    payment_provider_id = factory.SelfAttribute("payment_provider.id")
    payment_provider = factory.SubFactory("app.factories.PaymentProviderFactory", merchant_identifiers=[])
    location = generic.text.random.randstr(length=250)
    postcode = generic.address.zip_code()

    # matched_transactions = s.orm.relationship("MatchedTransaction", backref="merchant_identifier")
    matched_transactions = factory.RelatedFactoryList("app.factories.MatchedTransaction", "merchant_identifier", size=3)


class SchemeTransactionFactory(factory.Factory):
    class Meta:
        model = models.SchemeTransaction

    merchant_identifier_ids = generic.numbers.random.randints(amount=5, a=1, b=1000000)
    provider_slug = generic.text.random.randstr(length=50)
    payment_provider_slug = generic.text.random.randstr(length=50)
    transaction_id = generic.text.random.randstr(unique=True, length=50)
    # 2020-08-05 17:28:52
    # 2013-10-05 04:08:16
    transaction_date = generic.datetime.formatted_datetime(fmt="%Y-%m-%d %H:%M:%S")
    has_time = generic.development.boolean()
    spend_amount = generic.numbers.integer_number(start=1)
    spend_multiplier = generic.numbers.integer_number(start=1)
    spend_currency = generic.business.currency_iso_code(allow_random=True)
    status = generic.choice(items=[x.value for x in models.TransactionStatus])
    auth_code = generic.text.random.randstr(length=20)
    match_group = generic.text.random.randstr(length=36)
    extra_fields = generic.json_provider.json()

    # matched_transactions = s.orm.relationship("MatchedTransaction", backref="scheme_transaction")
    matched_transactions = factory.RelatedFactoryList("app.factories.MatchedTransaction", "scheme_transaction", size=3)


class PaymentTransactionFactory(factory.Factory):
    class Meta:
        model = models.PaymentTransaction

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
    user_identity = factory.SubFactory("app.factories.UserIdentityFactory")
    match_group = generic.text.random.randstr(length=36)
    extra_fields = generic.json_provider.json()

    matched_transactions = factory.RelatedFactoryList("app.factories.MatchedTransaction", "payment_transaction", size=3)


class MatchedTransactionFactory(factory.Factory):
    class Meta:
        model = models.MatchedTransaction

    merchant_identifier_id = factory.SelfAttribute("merchant_identifier.id")
    merchant_identifier = factory.SubFactory("app.factories.MerchantIdentifierFactory")
    transaction_id = generic.text.random.randstr(unique=True, length=100)
    transaction_date = generic.datetime.formatted_datetime(fmt="%Y-%m-%d %H:%M:%S")
    spend_amount = generic.numbers.integer_number(start=1)
    spend_multiplier = generic.numbers.integer_number(start=1)
    spend_currency = generic.business.currency_iso_code(allow_random=True)
    card_token = generic.text.random.randstr(length=100)
    matching_type = generic.choice(items=[x.value for x in models.MatchingType])
    status = generic.choice(items=[x.value for x in models.MatchedTransactionStatus])
    payment_transaction_id = factory.SelfAttribute("payment_transaction.id")
    payment_transaction = factory.SubFactory("app.factories.PaymentTransactionFactory")
    scheme_transaction_id = factory.SelfAttribute("scheme_transaction.id")
    scheme_transaction = factory.SubFactory("app.factories.SchemeTransactionFactory")
    extra_fields = generic.json_provider.json()

    pending_exports = factory.RelatedFactoryList(
        "app.exports.factories.PendingExportFactory", "matched_transaction", size=3
    )


class UserIdentityFactory(factory.Factory):
    class Meta:
        model = models.UserIdentity

    loyalty_id = generic.text.random.randstr(length=250)
    scheme_account_id = generic.numbers.integer_number(start=1)
    user_id = generic.numbers.integer_number(start=1)
    credentials = generic.cryptographic.token_urlsafe()
    first_six = generic.random.generate_string("0123456789", length=6)
    last_four = generic.random.generate_string("0123456789", length=4)

    payment_transaction = factory.RelatedFactoryList("app.factories.PaymentTransaction", "user_identity", size=3)
