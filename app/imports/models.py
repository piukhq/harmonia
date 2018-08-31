from sqlalchemy import Column, Integer, String, JSON, DateTime, UniqueConstraint

from app.db import Base, auto_repr
from app import postgres


@auto_repr
class ImportTransaction(Base):
    __tablename__ = 'import_transactions'
    __table_args__ = (UniqueConstraint('provider_slug', 'transaction_id', name='_slug_tid_uc'), )

    id = Column(Integer, primary_key=True)
    transaction_id = Column(String(50), nullable=False)
    provider_slug = Column(String(50), nullable=False)
    source = Column(String(50), nullable=True)
    data = Column(JSON)

    created_at = Column(DateTime, server_default=postgres.utcnow())
    updated_at = Column(DateTime, onupdate=postgres.utcnow())

    def __str__(self):
        return ('<ImportTransaction('
                f"id={self.id}, "
                f"transaction_id={self.transaction_id}, "
                f"provider_slug={self.provider_slug}"
                ')>')
