from sqlalchemy import Column, String, JSON, UniqueConstraint

from app.db import Base, auto_repr, ModelMixin


@auto_repr
class ImportTransaction(Base, ModelMixin):
    __tablename__ = 'import_transaction'
    __table_args__ = (UniqueConstraint('provider_slug', 'transaction_id', name='_slug_tid_uc'), )

    transaction_id = Column(String(50), nullable=False)
    provider_slug = Column(String(50), nullable=False)
    source = Column(String(500), nullable=True)
    data = Column(JSON)
