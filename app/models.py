from enum import Enum

import sqlalchemy as s
from sqlalchemy.dialects import postgresql as psql

from app.db import Base, ModelMixin, auto_repr, auto_str

# import other module's models here to be recognised by alembic.
from app.imports.models import ImportTransaction  # noqa
from app.exports.models import PendingExport, ExportTransaction, FileSequenceNumber  # noqa


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
    store_id = s.Column(s.String(50), nullable=True)
    loyalty_scheme_id = s.Column(s.Integer, s.ForeignKey("loyalty_scheme.id"))
    payment_provider_id = s.Column(s.Integer, s.ForeignKey("payment_provider.id"))
    location = s.Column(s.String(250), nullable=False)
    postcode = s.Column(s.String(16), nullable=False)

    matched_transactions = s.orm.relationship("MatchedTransaction", backref="merchant_identifier")


class TransactionStatus(Enum):
    PENDING = 0
    MATCHED = 1


@auto_repr
@auto_str("id", "transaction_id", "provider_slug", "payment_provider_slug")
class SchemeTransaction(Base, ModelMixin):
    __tablename__ = "scheme_transaction"

    merchant_identifier_ids = s.Column(psql.ARRAY(s.Integer))
    provider_slug = s.Column(s.String(50), nullable=False)  # hermes scheme slug
    payment_provider_slug = s.Column(s.String(50), nullable=False)  # hermes payment card slug
    transaction_id = s.Column(s.String(100), nullable=False)  # unique identifier assigned by the merchant
    transaction_date = s.Column(s.DateTime(timezone=True), nullable=False)  # date this transaction was originally made
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
