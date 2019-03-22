import typing as t

import sqlalchemy as s
from redis import StrictRedis
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound  # noqa

from app import postgres, encoding
import settings

engine = s.create_engine(settings.POSTGRES_DSN, json_serializer=encoding.dumps, json_deserializer=encoding.loads)

Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()  # type: t.Any


def get_or_create(model: t.Type[Base], defaults: t.Optional[dict] = None, **kwargs) -> t.Tuple[Base, bool]:
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    else:
        params = {**kwargs}
        if defaults:
            params.update(defaults)
        instance = model(**params)
        session.add(instance)
        return instance, True


def auto_repr(cls):
    """
    Generates a __repr__ method for the wrapped class that contains all the member
    variables.
    """

    def __repr__(self):
        return "{}({})".format(
            type(self).__name__,
            ", ".join(f"{col.name}={repr(getattr(self, col.name))}" for col in self.__table__.columns),
        )

    cls.__repr__ = __repr__
    return cls


def auto_str(*fields):
    def decorator(cls):
        def __str__(self):
            field_values = (f"{k}={repr(getattr(self, k))}" for k in fields)
            return f"{type(self).__name__}({', '.join(field_values)})"

        cls.__str__ = __str__
        return cls

    return decorator


class ModelMixin:
    id = s.Column(s.Integer, primary_key=True)

    created_at = s.Column(s.DateTime, server_default=postgres.utcnow())
    updated_at = s.Column(s.DateTime, onupdate=postgres.utcnow())


redis = StrictRedis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASS,
    socket_timeout=1,
    socket_connect_timeout=3,
    socket_keepalive=True,
    retry_on_timeout=False,
)
