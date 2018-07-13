from sqlalchemy import Column, Integer, String

from app.db import Base

# import other module's models here to be recognised by alembic.
from app.imports.models import ImportTransaction  # noqa


class SchemeTransaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True)
    transaction_id = Column(String)
    pence = Column(Integer)
    points_earned = Column(Integer)
    card_id = Column(String)
    total_points = Column(Integer)

    def __str__(self):
        return (
            '<SchemeTransaction('
            f"id={self.id}, "
            f"transaction_id={self.transaction_id}, "
            f"pence={self.pence}, "
            f"points_earned={self.points_earned}, "
            f"card_id={self.card_id}, "
            f"total_points={self.total_points}"
            ')>')
