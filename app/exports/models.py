import sqlalchemy as s

from app.db import Base, ModelMixin, auto_repr, auto_str


@auto_repr
@auto_str("id", "matched_transaction_id")
class PendingExport(Base, ModelMixin):
    __tablename__ = "pending_export"

    provider_slug = s.Column(s.String(50), nullable=False, index=True)
    matched_transaction_id = s.Column(s.Integer, s.ForeignKey("matched_transaction.id"))
    retry_count = s.Column(s.Integer, nullable=False, default=0)
    retry_at = s.Column(s.DateTime, nullable=True, index=True)


@auto_repr
class ExportTransaction(Base, ModelMixin):
    __tablename__ = "export_transaction"
    __table_args__ = (s.UniqueConstraint("provider_slug", "transaction_id", name="_slug_tid_et_uc"),)

    matched_transaction_id = s.Column(s.Integer, s.ForeignKey("matched_transaction.id"))
    transaction_id = s.Column(s.String(100), nullable=False)
    provider_slug = s.Column(s.String(50), nullable=False)
    destination = s.Column(s.String(500), nullable=True)
    data = s.Column(s.JSON)


@auto_repr
class FileSequenceNumber(Base, ModelMixin):
    __tablename__ = "file_sequence_number"

    provider_slug = s.Column(s.String(50), nullable=False, index=True)
    next_value = s.Column(s.Integer, nullable=False)
