from sqlalchemy import Column, Integer, String, JSON, UniqueConstraint

from app.db import Base


class ImportTransaction(Base):
    __tablename__ = 'import_transactions'
    __table_args__ = (
        UniqueConstraint('provider_slug', 'transaction_id', name='_slug_tid_uc'),
    )

    id = Column(Integer, primary_key=True)
    transaction_id = Column(String)
    provider_slug = Column(String)
    data = Column(JSON)

    def __str__(self):
        return (
            '<ImportTransaction('
            f"id={self.id}, "
            f"transaction_id={self.transaction_id}, "
            f"provider_slug={self.provider_slug}"
            ')>')
