import sqlalchemy as s
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app import postgres, encoding
import settings


db_engine = s.create_engine(settings.POSTGRES_DSN, json_serializer=encoding.dumps, json_deserializer=encoding.loads)
Session = sessionmaker(bind=db_engine)

Base = declarative_base()


def auto_repr(cls):
    """Generates a __repr__ method for the wrapped class that contains all the member variables"""

    def __repr__(self):
        return '{}({})'.format(
            type(self).__name__, ', '.join(f"{k}={repr(v)}" for k, v in vars(self).items() if not k.startswith('_')))

    cls.__repr__ = __repr__
    return cls


class ModelMixin:
    id = s.Column(s.Integer, primary_key=True)

    created_at = s.Column(s.DateTime, server_default=postgres.utcnow())
    updated_at = s.Column(s.DateTime, onupdate=postgres.utcnow())
