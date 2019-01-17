from enum import Enum

import sqlalchemy as s

from app.db import Base, ModelMixin, auto_repr, auto_str

# import other module's models here to be recognised by alembic.
from app.imports.models import ImportTransaction  # noqa
from app.exports.models import PendingExport, ExportTransaction  # noqa


@auto_repr
@auto_str("id", "slug")
class LoyaltyScheme(Base, ModelMixin):
    __tablename__ = "loyalty_scheme"

    slug = s.Column(s.String(50), nullable=False)  # hermes scheme slug

    merchant_identifiers = s.orm.relationship(
        "MerchantIdentifier", backref="loyalty_scheme"
    )


@auto_repr
@auto_str("id", "slug")
class PaymentProvider(Base, ModelMixin):
    __tablename__ = "payment_provider"

    slug = s.Column(s.String(50), nullable=False)  # hermes payment card slug

    merchant_identifiers = s.orm.relationship(
        "MerchantIdentifier", backref="payment_provider"
    )


@auto_repr
@auto_str("id", "mid")
class MerchantIdentifier(Base, ModelMixin):
    __tablename__ = "merchant_identifier"

    mid = s.Column(s.String(50), nullable=False, index=True)
    loyalty_scheme_id = s.Column(s.Integer, s.ForeignKey("loyalty_scheme.id"))
    payment_provider_id = s.Column(s.Integer, s.ForeignKey("payment_provider.id"))
    location = s.Column(s.String(250), nullable=True)
    postcode = s.Column(s.String(16), nullable=True)

    scheme_transactions = s.orm.relationship(
        "SchemeTransaction", backref="merchant_identifier"
    )
    payment_transactions = s.orm.relationship(
        "PaymentTransaction", backref="merchant_identifier"
    )
    matched_transactions = s.orm.relationship(
        "MatchedTransaction", backref="merchant_identifier"
    )


class TransactionStatus(Enum):
    PENDING = 0
    MATCHED = 1


@auto_repr
@auto_str("id", "transaction_id")
class SchemeTransaction(Base, ModelMixin):
    __tablename__ = "scheme_transaction"

    merchant_identifier_id = s.Column(s.Integer, s.ForeignKey("merchant_identifier.id"))
    transaction_id = s.Column(
        s.String(100), nullable=False
    )  # unique identifier assigned by the merchant
    transaction_date = s.Column(
        s.DateTime, nullable=False
    )  # date this transaction was originally made
    spend_amount = s.Column(
        s.Integer, nullable=False
    )  # the amount of money that was involved in the transaction
    spend_multiplier = s.Column(
        s.Integer, nullable=False
    )  # amount that spend_amount was multiplied by
    spend_currency = s.Column(
        s.String(3), nullable=False
    )  # ISO 4217 alphabetic code for the currency involved
    points_amount = s.Column(
        s.Integer
    )  # number of points that were involved in the transaction
    points_multiplier = s.Column(
        s.Integer
    )  # amount points_amount was multiplied by to make it integral
    status = s.Column(
        s.Enum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING
    )

    extra_fields = s.Column(s.JSON)  # any extra data used for exports

    matched_transactions = s.orm.relationship(
        "MatchedTransaction", backref="scheme_transaction"
    )


@auto_repr
@auto_str("id", "transaction_id")
class PaymentTransaction(Base, ModelMixin):
    __tablename__ = "payment_transaction"

    merchant_identifier_id = s.Column(s.Integer, s.ForeignKey("merchant_identifier.id"))
    transaction_id = s.Column(
        s.String(100), nullable=False
    )  # unique identifier assigned by the provider
    transaction_date = s.Column(
        s.DateTime, nullable=False
    )  # date this transaction was originally made
    spend_amount = s.Column(
        s.Integer, nullable=False
    )  # the amount of money that was involved in the transaction
    spend_multiplier = s.Column(
        s.Integer, nullable=False
    )  # amount that spend_amount was multiplied by
    spend_currency = s.Column(
        s.String(3), nullable=False
    )  # ISO 4217 alphabetic code for the currency involved
    card_token = s.Column(s.String(100))  # token assigned to the card that was used
    status = s.Column(
        s.Enum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING
    )

    extra_fields = s.Column(s.JSON)  # any extra data used for exports

    matched_transactions = s.orm.relationship(
        "MatchedTransaction", backref="payment_transaction"
    )


class MatchingType(Enum):
    SPOTTED = 0  # payment tx identified with no scheme feed available
    LOYALTY = 1  # payment tx identified with loyalty tx scheme feed available
    NON_LOYALTY = 2  # payment tx identified with non-loyalty tx scheme feed available
    MIXED = 3  # payment tx identified with full tx scheme feed available


class MatchedTransactionStatus(Enum):
    PENDING = 0  # awaiting export
    EXPORTED = 1  # sent to provider


@auto_repr
@auto_str("id", "transaction_id")
class MatchedTransaction(Base, ModelMixin):
    __tablename__ = "matched_transaction"

    merchant_identifier_id = s.Column(s.Integer, s.ForeignKey("merchant_identifier.id"))
    transaction_id = s.Column(
        s.String(100), nullable=False
    )  # unique identifier assigned by the merchant/provider
    transaction_date = s.Column(
        s.DateTime, nullable=False
    )  # date this transaction was originally made
    spend_amount = s.Column(
        s.Integer, nullable=False
    )  # the amount of money that was involved in the transaction
    spend_multiplier = s.Column(
        s.Integer, nullable=False
    )  # amount that spend_amount was multiplied by
    spend_currency = s.Column(
        s.String(3), nullable=False
    )  # ISO 4217 alphabetic code for the currency involved
    points_amount = s.Column(
        s.Integer
    )  # number of points that were involved in the transaction
    points_multiplier = s.Column(
        s.Integer
    )  # amount points_amount was multiplied by to make it integral
    card_token = s.Column(s.String(100))  # token assigned to the card that was used
    matching_type = s.Column(
        s.Enum(MatchingType), nullable=False
    )  # type of matching, see MatchingType for options
    status = s.Column(
        s.Enum(MatchedTransactionStatus),
        nullable=False,
        default=MatchedTransactionStatus.PENDING,
    )
    payment_transaction_id = s.Column(s.Integer, s.ForeignKey("payment_transaction.id"))
    scheme_transaction_id = s.Column(s.Integer, s.ForeignKey("scheme_transaction.id"))

    user_identity = s.orm.relationship("UserIdentity", uselist=False, back_populates="matched_transaction")

    extra_fields = s.Column(
        s.JSON
    )  # combination of the same field on the scheme and payment transaction models


@auto_repr
class UserIdentity(Base, ModelMixin):
    __tablename__ = "user_identity"

    loyalty_id = s.Column(s.String(250), nullable=False)
    scheme_account_id = s.Column(s.Integer, nullable=False)
    user_id = s.Column(s.Integer, nullable=False)
    credentials = s.Column(s.Text, nullable=False)

    matched_transaction_id = s.Column(s.Integer, s.ForeignKey("matched_transaction.id"))
    matched_transaction = s.orm.relationship("MatchedTransaction", back_populates="user_identity")
