import typing as t
from contextlib import contextmanager
from uuid import uuid4

import sqlalchemy as s
from redis import Redis
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.exc import NoResultFound  # noqa
from sqlalchemy.pool import NullPool

import settings
from app import encoding, postgres
from app.reporting import get_logger

engine = s.create_engine(
    settings.POSTGRES_DSN,
    connect_args=settings.POSTGRES_CONNECT_ARGS,
    poolclass=NullPool,
    json_serializer=encoding.dumps,
    json_deserializer=encoding.loads,
    echo=settings.TRACE_QUERY_SQL,
)

SessionMaker = sessionmaker(bind=engine)
Base = declarative_base()  # type: t.Any

log = get_logger("db")


@contextmanager
def session_scope() -> t.Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session = SessionMaker()
    sid = str(uuid4())
    log.debug(f"Session {sid} created.")
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        log.warning(f"Session {sid} rolled back.")
        raise
    finally:
        session.close()
        log.debug(f"Session {sid} closed.")


# based on the following stackoverflow answer:
# https://stackoverflow.com/a/30004941
def run_query(fn, *, session: Session, attempts: int = 2, read_only: bool = False, description: t.Optional[str] = None):
    if settings.TRACE_QUERY_DESCRIPTIONS:
        if description is None:
            description = repr(fn)

        if read_only:
            query_type_str = "read"
        else:
            query_type_str = "read/write"
        log.debug(f'Attempting {query_type_str} query for function "{description}" with {attempts} attempts')

    while attempts > 0:
        attempts -= 1
        try:
            return fn()
        except DBAPIError as ex:
            log.debug(f"Attempt failed: {type(ex).__name__} {ex}")
            if not read_only:
                session.rollback()
            if attempts > 0 and ex.connection_invalidated:
                log.warning(f"Database query {fn} failed with {type(ex).__name__}. {attempts} attempt(s) remaining.")
            else:
                raise


def _get_one_or_none(model: t.Type[Base], *, session: Session, **kwargs) -> t.Optional[Base]:
    return run_query(
        lambda: session.query(model).filter_by(**kwargs).one_or_none(),
        session=session,
        read_only=True,
        description=f"find {model.__name__} object for get_or_create",
    )


def get_or_create(
    model: t.Type[Base], *, session: Session, defaults: t.Optional[dict] = None, **kwargs
) -> t.Tuple[Base, bool]:
    instance = _get_one_or_none(model, session=session, **kwargs)
    if instance:
        return instance, False
    else:
        params = {**kwargs}
        if defaults:
            params.update(defaults)

        def add_instance():
            instance = model(**params)
            session.add(instance)
            session.commit()
            return instance

        try:
            return (
                run_query(
                    add_instance, session=session, description=f"create {model.__name__} object for get_or_create"
                ),
                True,
            )
        except IntegrityError:
            return _get_one_or_none(model, session=session, **kwargs), False


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


redis = Redis.from_url(
    settings.REDIS_URL,
    socket_connect_timeout=3,
    socket_keepalive=True,
    retry_on_timeout=False,
    decode_responses=True,
)

# Same as above but does not decode responses. Used as the RQ connection.
redis_raw = Redis.from_url(
    settings.REDIS_URL,
    socket_connect_timeout=3,
    socket_keepalive=True,
    retry_on_timeout=False,
)


def redis_scan(pattern: str) -> t.Iterator[str]:
    """
    simply wraps `redis.scan_iter(pattern)` to provide correct type hints.
    scan_iter should return `str` as long as decode_responses is True
    """
    yield from redis.scan_iter(pattern)  # type: ignore
