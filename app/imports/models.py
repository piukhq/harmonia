import sqlalchemy as s

from app.db import Base, auto_repr, ModelMixin


@auto_repr
class ImportTransaction(Base, ModelMixin):
    __tablename__ = "import_transaction"
    __table_args__ = (s.UniqueConstraint("provider_slug", "transaction_id", name="_slug_tid_it_uc"),)

    transaction_id = s.Column(s.String(100), nullable=False)
    provider_slug = s.Column(s.String(50), nullable=False)
    identified = s.Column(s.Boolean, nullable=False)
    match_group = s.Column(s.String(36), nullable=False)
    source = s.Column(s.String(500), nullable=True)
    data = s.Column(s.JSON)


@auto_repr
class ImportFileLog(Base, ModelMixin):
    __tablename__ = "import_file_log"

    provider_slug = s.Column(s.String(50), nullable=False)
    file_name = s.Column(s.String(500), nullable=False)
    imported = s.Column(s.Boolean, nullable=False, default=False)
    date_range_from = s.Column(s.DateTime, nullable=True)
    date_range_to = s.Column(s.DateTime, nullable=True)
    transaction_count = s.Column(s.Integer, nullable=True)
