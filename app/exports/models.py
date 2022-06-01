from enum import Enum

import sqlalchemy as s

from app.db import Base, ModelMixin, auto_repr, auto_str
from app.encryption import decrypt_credentials
from app.feeds import FeedType


class ExportTransactionStatus(Enum):
    PENDING = 0  # awaiting export
    EXPORTED = 1  # sent to provider
    EXPORT_FAILED = 2  # failed to export after retrying


@auto_repr
@auto_str("id", "export_transaction_id")
class PendingExport(Base, ModelMixin):
    __tablename__ = "pending_export"

    provider_slug = s.Column(s.String(50), nullable=False, index=True)
    export_transaction_id = s.Column(s.Integer, s.ForeignKey("export_transaction.id"))
    retry_count = s.Column(s.Integer, nullable=False, default=0)
    retry_at = s.Column(s.DateTime, nullable=True, index=True)


@auto_repr
@auto_str("id", "transaction_id")
class ExportTransaction(Base, ModelMixin):
    __tablename__ = "export_transaction"

    transaction_id = s.Column(s.String(100), nullable=False)  # unique identifier assigned by the merchant/provider
    feed_type = s.Column(s.Enum(FeedType), nullable=True)  # can be null, matching has no single feed type
    provider_slug = s.Column(s.String(50), nullable=False)  # merchant slug
    transaction_date = s.Column(s.DateTime, nullable=False)  # date this transaction was originally made
    spend_amount = s.Column(s.Integer, nullable=False)  # the amount of money that was involved in the transaction
    spend_currency = s.Column(s.String(3), nullable=False)  # ISO 4217 alphabetic code for the currency involved
    loyalty_id = s.Column(s.String(100), nullable=False)  # Merchant loyalty identifier/membership number
    mid = s.Column(s.String(50), nullable=False)  # merchant identifier for identifying the store purchase made
    location_id = s.Column(s.String(50), nullable=True)
    merchant_internal_id = s.Column(s.String(50), nullable=True)
    user_id = s.Column(s.Integer, nullable=False)
    scheme_account_id = s.Column(s.Integer, nullable=False)
    payment_card_account_id = s.Column(s.Integer, nullable=True)
    credentials = s.Column(s.Text, nullable=False)
    auth_code = s.Column(s.String(20), nullable=False, default="")
    approval_code = s.Column(s.String(20), nullable=False, default="")
    status = s.Column(s.Enum(ExportTransactionStatus), nullable=False, default=ExportTransactionStatus.PENDING)
    settlement_key = s.Column(s.String(100), nullable=True)  # used to group auth & settled transactions
    last_four = s.Column(s.String(4), nullable=True)
    expiry_month = s.Column(s.Integer, nullable=True)
    expiry_year = s.Column(s.Integer, nullable=True)
    payment_provider_slug = s.Column(s.String(50), nullable=True)  # payment card provider slug - visa, amex etc

    pending_exports = s.orm.relationship("PendingExport", backref="export_transaction")

    @property
    def decrypted_credentials(self):
        return decrypt_credentials(self.credentials)


@auto_repr
class FileSequenceNumber(Base, ModelMixin):
    __tablename__ = "file_sequence_number"

    provider_slug = s.Column(s.String(50), nullable=False, index=True)
    next_value = s.Column(s.Integer, nullable=False)
