import typing as t
import logging
import os

from sentry_sdk.integrations.flask import FlaskIntegration
import sentry_sdk


class ConfigVarRequiredError(Exception):
    pass


def getenv(
    key: str, default: str = None, conv: t.Callable = str, required: bool = True
) -> t.Any:
    """If `default` is None, then the var is non-optional."""
    var = os.getenv(key, default)
    if var is None and required is True:
        raise ConfigVarRequiredError(
            f"Configuration variable '{key}' is required but was not provided."
        )
    elif var is not None:
        return conv(var)
    else:
        return None


def boolconv(s: str) -> bool:
    return s.lower() in ["true", "t", "yes"]


# Global logging level. Applies to any logger obtained through `app.reporting.get_logger`.
# https://docs.python.org/3/library/logging.html#logging-levels
LOG_LEVEL = getattr(logging, getenv("TXM_LOG_LEVEL", default="debug").upper())

# Debug mode toggle. Running in debug mode disables a lot of error handling.
DEBUG = getenv("TXM_DEBUG", default="false", conv=boolconv)

# Canonical name of the environment we're running in.
# e.g. dev, staging, production
ENVIRONMENT_ID = getenv("TXM_ENVIRONMENT_ID", default="unknown").lower()

# Connection string for Postgres.
# Postgres is used as the main database for the transaction matching system.
# https://www.postgresql.org/docs/10/static/libpq-connect.html#LIBPQ-CONNSTRING
POSTGRES_DSN = getenv("TXM_POSTGRES_DSN")

# Connection string for Redis.
# Redis is used as a configuration store that can be updated at runtime.
# https://redis-py.readthedocs.io/en/latest/#redis.StrictRedis.from_url
REDIS_DSN = getenv("TXM_REDIS_DSN")

# The prefix used on every Redis key.
REDIS_KEY_PREFIX = "txmatch"

# Sentry project data source name.
# https://docs.sentry.io/quickstart/#about-the-dsn
SENTRY_DSN = getenv("TXM_SENTRY_DSN", required=False)

if SENTRY_DSN is not None:
    sentry_sdk.init(
        dsn=SENTRY_DSN, environment=ENVIRONMENT_ID, integrations=[FlaskIntegration()]
    )

# JSON encoding with custom extensions. Used in queue messages, postgres JSON field storage, et cetera.
JSON_SERIALIZER = "txmatch+json"
