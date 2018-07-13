from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker

import settings


db_engine = create_engine(settings.POSTGRES_DSN)
Session = sessionmaker(bind=db_engine)

Base = declarative_base()


class SchemeTransaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True)
    transaction_id = Column(String)
    pence = Column(Integer)
    points_earned = Column(Integer)
    card_id = Column(String)
    total_points = Column(Integer)
