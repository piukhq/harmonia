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


generic = Generic('en-gb')
generic.add_provider(JSONProvider)


# One side
class LoyaltySchemeFactory(factory.Factory):
    class Meta:
        model = models.LoyaltyScheme

    slug = generic.text.random.randstr(unique=True, length=50)
    merchant_identifiers = factory.RelatedFactoryList("app.factories.MerchantIdentifier", 'loyalty_scheme', size=3)
    # merchant_identifiers = s.orm.relationship("MerchantIdentifier", backref="loyalty_scheme")


class PaymentProviderFactory(factory.Factory):
    class Meta:
        model = models.PaymentProvider

    slug = generic.text.random.randstr(unique=True, length=50)
    merchant_identifiers = factory.RelatedFactoryList("app.factories.MerchantIdentifier", 'payment_provider', size=3)


# Many side
class MerchantIdentifier(factory.Factory):
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
    matched_transactions = factory.RelatedFactoryList("app.factories.MatchedTransaction", 'merchant_identifier', size=3)


class TransactionStatus(Enum):
    PENDING = 0
    MATCHED = 1

# TODO: use lazy when building from other simple attributes e.g. id = lazy_attribute(lambda o: fake.uuid4())
# matched_transaction_id = factory.SubFactory("app.factories.MatchedTransactionFactory")
# transaction_id = generic.text.random.randstr(unique=True, length=50)
# provider_slug = generic.text.random.randstr(length=50)
# destination = generic.text.random.randstr(length=500)
# data = generic.json_provider.json()
# next_value = generic.numbers.integer_number(start=1)

class SchemeTransactionFactory(factory.Factory):
    class Meta:
        model = models.SchemeTransaction

    merchant_identifier_ids = generic.numbers.random.randints(amount=5, a=1, b=1000000)
    provider_slug = generic.text.random.randstr(length=50)
    payment_provider_slug = generic.text.random.randstr(length=50)
    transaction_id = generic.text.random.randstr(unique=True, length=50)
    transaction_date = s.Column(s.DateTime(timezone=True), nullable=False, index=True)  # date the transaction was made
    has_time = s.Column(s.Boolean, nullable=False, default=False)  # indicates if a time is sent with the transaction
    spend_amount = s.Column(s.Integer, nullable=False)  # the amount of money that was involved in the transaction
    spend_multiplier = s.Column(s.Integer, nullable=False)  # amount that spend_amount was multiplied by
    spend_currency = s.Column(s.String(3), nullable=False)  # ISO 4217 alphabetic code for the currency involved
    status = s.Column(s.Enum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING)
    auth_code = s.Column(s.String(20), nullable=False, default="")
    match_group = s.Column(s.String(36), nullable=False, index=True)  # the group this transaction was imported in
    extra_fields = s.Column(psql.JSON)  # any extra data used for exports

    matched_transactions = s.orm.relationship("MatchedTransaction", backref="scheme_transaction")


@auto_repr
@auto_str("id", "transaction_id", "provider_slug")
class PaymentTransaction(Base, ModelMixin):
    __tablename__ = "payment_transaction"

    merchant_identifier_ids = s.Column(psql.ARRAY(s.Integer))
    provider_slug = s.Column(s.String(50), nullable=False)  # hermes payment card slug
    transaction_id = s.Column(s.String(100), nullable=False)  # unique identifier assigned by the provider
    settlement_key = s.Column(s.String(100), nullable=True, index=True)  # key to match auth & settled transactions
    transaction_date = s.Column(s.DateTime(timezone=True), nullable=False)  # date this transaction was originally made
    has_time = s.Column(s.Boolean, nullable=False, default=False)  # indicates if a time is sent with the transaction
    spend_amount = s.Column(s.Integer, nullable=False)  # the amount of money that was involved in the transaction
    spend_multiplier = s.Column(s.Integer, nullable=False)  # amount that spend_amount was multiplied by
    spend_currency = s.Column(s.String(3), nullable=False)  # ISO 4217 alphabetic code for the currency involved
    card_token = s.Column(s.String(100), nullable=False)  # token assigned to the card that was used
    status = s.Column(s.Enum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING)
    auth_code = s.Column(s.String(20), nullable=False, default="")
    user_identity_id = s.Column(s.Integer, s.ForeignKey("user_identity.id"))
    match_group = s.Column(s.String(36), nullable=False, index=True)  # currently unused
    extra_fields = s.Column(psql.JSON)  # any extra data used for exports

    user_identity = s.orm.relationship("UserIdentity", uselist=False, back_populates="payment_transaction")
    matched_transactions = s.orm.relationship("MatchedTransaction", backref="payment_transaction")


class MatchingType(Enum):
    SPOTTED = 0  # payment tx identified with no scheme feed available
    LOYALTY = 1  # payment tx identified with loyalty tx scheme feed available
    NON_LOYALTY = 2  # payment tx identified with non-loyalty tx scheme feed available
    MIXED = 3  # payment tx identified with full tx scheme feed available
    FORCED = 4  # match was created manually via redress process


class MatchedTransactionStatus(Enum):
    PENDING = 0  # awaiting export
    EXPORTED = 1  # sent to provider


@auto_repr
@auto_str("id", "transaction_id")
class MatchedTransaction(Base, ModelMixin):
    __tablename__ = "matched_transaction"

    merchant_identifier_id = s.Column(s.Integer, s.ForeignKey("merchant_identifier.id"))
    transaction_id = s.Column(s.String(100), nullable=False)  # unique identifier assigned by the merchant/provider
    transaction_date = s.Column(s.DateTime, nullable=False)  # date this transaction was originally made
    spend_amount = s.Column(s.Integer, nullable=False)  # the amount of money that was involved in the transaction
    spend_multiplier = s.Column(s.Integer, nullable=False)  # amount that spend_amount was multiplied by
    spend_currency = s.Column(s.String(3), nullable=False)  # ISO 4217 alphabetic code for the currency involved
    card_token = s.Column(s.String(100), nullable=False)  # token assigned to the card that was used
    matching_type = s.Column(s.Enum(MatchingType), nullable=False)  # type of matching, see MatchingType for options
    status = s.Column(s.Enum(MatchedTransactionStatus), nullable=False, default=MatchedTransactionStatus.PENDING)
    payment_transaction_id = s.Column(s.Integer, s.ForeignKey("payment_transaction.id"))
    scheme_transaction_id = s.Column(s.Integer, s.ForeignKey("scheme_transaction.id"))

    extra_fields = s.Column(psql.JSON)  # combination of the same field on the scheme and payment transaction models

    pending_exports = s.orm.relationship("PendingExport", backref="matched_transaction")


@auto_repr
@auto_str("id", "user_id", "scheme_account_id")
class UserIdentity(Base, ModelMixin):
    __tablename__ = "user_identity"

    loyalty_id = s.Column(s.String(250), nullable=False)
    scheme_account_id = s.Column(s.Integer, nullable=False)
    user_id = s.Column(s.Integer, nullable=False)
    credentials = s.Column(s.Text, nullable=False)
    first_six = s.Column(s.Text, nullable=False)
    last_four = s.Column(s.Text, nullable=False)

    payment_transaction = s.orm.relationship("PaymentTransaction", uselist=False, back_populates="user_identity")



