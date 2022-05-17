from enum import Enum

import sqlalchemy as s
from sqlalchemy.dialects import postgresql as psql

# import other module's models here to be recognised by alembic.
from app.config.models import ConfigItem  # noqa
from app.db import Base, ModelMixin, auto_repr, auto_str
from app.encryption import decrypt_credentials
from app.exports.models import ExportTransaction, FileSequenceNumber, PendingExport  # noqa
from app.feeds import FeedType
from app.imports.models import ImportFileLog, ImportTransaction  # noqa


@auto_repr
@auto_str("id", "slug")
class LoyaltyScheme(Base, ModelMixin):
    __tablename__ = "loyalty_scheme"

    slug = s.Column(s.String(50), index=True, unique=True, nullable=False)  # hermes scheme slug

    merchant_identifiers = s.orm.relationship("MerchantIdentifier", backref="loyalty_scheme")


@auto_repr
@auto_str("id", "slug")
class PaymentProvider(Base, ModelMixin):
    __tablename__ = "payment_provider"

    slug = s.Column(s.String(50), index=True, unique=True, nullable=False)  # hermes payment card slug

    merchant_identifiers = s.orm.relationship("MerchantIdentifier", backref="payment_provider")


@auto_repr
@auto_str("id", "mid")
class MerchantIdentifier(Base, ModelMixin):
    __tablename__ = "merchant_identifier"
    __table_args__ = (s.UniqueConstraint("mid", "payment_provider_id", name="_mid_provider_mi_uc"),)

    mid = s.Column(s.String(50), nullable=False)
    location_id = s.Column(s.String(50), nullable=True)
    merchant_internal_id = s.Column(s.String(50), nullable=True)
    loyalty_scheme_id = s.Column(s.Integer, s.ForeignKey("loyalty_scheme.id"))
    payment_provider_id = s.Column(s.Integer, s.ForeignKey("payment_provider.id"))
    location = s.Column(s.String(250), nullable=False)
    postcode = s.Column(s.String(16), nullable=False)

    matched_transactions = s.orm.relationship("MatchedTransaction", backref="merchant_identifier")


class TransactionStatus(Enum):
    PENDING = 0
    IMPORTED = 1
    MATCHED = 2
    EXPORTED = 3
    EXPORT_FAILED = 4


@auto_repr
@auto_str("id", "transaction_id")
class Transaction(Base, ModelMixin):
    __tablename__ = "transaction"
    __table_args__ = (s.UniqueConstraint("transaction_id", "feed_type", name="_transaction_id_feed_type_t_uc"),)

    # the type of transaction this is. unique together with the transaction ID.
    feed_type = s.Column(s.Enum(FeedType), nullable=False)

    # current state of the transaction.
    status = s.Column(s.Enum(TransactionStatus), nullable=False)

    # list of related merchant_identifier record IDs.
    merchant_identifier_ids = s.Column(psql.ARRAY(s.Integer))

    # hermes scheme & paymentcard slugs.
    merchant_slug = s.Column(s.String(50), nullable=False)
    payment_provider_slug = s.Column(s.String(50), nullable=False)

    # provider-specific transaction ID. unique together with the feed type.
    transaction_id = s.Column(s.String(100), nullable=False)

    # used to group auth & settled transactions together.
    settlement_key = s.Column(s.String(100), nullable=True, index=True)

    # the group this transaction was imported in
    match_group = s.Column(s.String(36), nullable=False, index=True)

    # per-feed transaction data
    transaction_date = s.Column(s.DateTime(timezone=True), nullable=False)
    has_time = s.Column(s.Boolean, nullable=False, default=False)
    spend_amount = s.Column(s.Integer, nullable=False)
    spend_multiplier = s.Column(s.Integer, nullable=False)
    spend_currency = s.Column(s.String(3), nullable=False)  # ISO 4217 alphabetic
    card_token = s.Column(s.String(100), nullable=True)  # null for merchant feed transactions
    first_six = s.Column(s.Text, nullable=True)
    last_four = s.Column(s.Text, nullable=True)
    auth_code = s.Column(s.String(20), nullable=False, default="")
    approval_code = s.Column(s.String(20), nullable=True, default="")


@auto_repr
@auto_str("id", "transaction_id", "provider_slug", "payment_provider_slug")
class SchemeTransaction(Base, ModelMixin):
    __tablename__ = "scheme_transaction"

    merchant_identifier_ids = s.Column(psql.ARRAY(s.Integer))
    provider_slug = s.Column(s.String(50), nullable=False)  # hermes scheme slug
    payment_provider_slug = s.Column(s.String(50), nullable=False)  # hermes payment card slug
    transaction_id = s.Column(s.String(100), nullable=False)  # unique identifier assigned by the merchant
    transaction_date = s.Column(s.DateTime(timezone=True), nullable=False, index=True)  # date the transaction was made
    has_time = s.Column(s.Boolean, nullable=False, default=False)  # indicates if a time is sent with the transaction
    spend_amount = s.Column(s.Integer, nullable=False)  # the amount of money that was involved in the transaction
    spend_multiplier = s.Column(s.Integer, nullable=False)  # amount that spend_amount was multiplied by
    spend_currency = s.Column(s.String(3), nullable=False)  # ISO 4217 alphabetic code for the currency involved
    first_six = s.Column(s.Text, nullable=True)  # first six digits of card number, if present
    last_four = s.Column(s.Text, nullable=True)  # last four digits of card number, if present
    status = s.Column(s.Enum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING)
    auth_code = s.Column(s.String(20), nullable=False, default="")
    match_group = s.Column(s.String(36), nullable=False, index=True)  # the group this transaction was imported in
    extra_fields = s.Column(psql.JSON)  # any extra data used for exports


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
    first_six = s.Column(s.Text, nullable=True)  # first six digits of card number, if present
    last_four = s.Column(s.Text, nullable=True)  # last four digits of card number, if present
    status = s.Column(s.Enum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING)
    auth_code = s.Column(s.String(20), nullable=False, default="")
    match_group = s.Column(s.String(36), nullable=False, index=True)  # currently unused
    extra_fields = s.Column(psql.JSON)  # any extra data used for exports


class MatchingType(Enum):
    SPOTTED = 0  # payment tx identified with no scheme feed available
    LOYALTY = 1  # payment tx identified with loyalty tx scheme feed available
    NON_LOYALTY = 2  # payment tx identified with non-loyalty tx scheme feed available
    MIXED = 3  # payment tx identified with full tx scheme feed available
    FORCED = 4  # match was created manually via redress process


class MatchedTransactionStatus(Enum):
    PENDING = 0  # awaiting export
    EXPORTED = 1  # sent to provider
    EXPORT_FAILED = 2  # failed to export after retrying


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

    extra_fields = s.Column(psql.JSON)  # combination of the same field on the scheme and payment transaction models


@auto_repr
@auto_str("id", "user_id", "scheme_account_id")
class UserIdentity(Base, ModelMixin):
    __tablename__ = "user_identity"

    transaction_id = s.Column(s.String, nullable=False, index=True)
    loyalty_id = s.Column(s.String(250), nullable=False)
    scheme_account_id = s.Column(s.Integer, nullable=False)
    user_id = s.Column(s.Integer, nullable=False)
    credentials = s.Column(s.Text, nullable=False)
    first_six = s.Column(s.Text, nullable=False)
    last_four = s.Column(s.Text, nullable=False)
    payment_card_account_id = s.Column(s.Integer, nullable=True)
    expiry_month = s.Column(s.Integer, nullable=True)
    expiry_year = s.Column(s.Integer, nullable=True)

    @property
    def decrypted_credentials(self):
        return decrypt_credentials(self.credentials)
