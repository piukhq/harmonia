import logging
import os

from sentry_sdk.integrations.flask import FlaskIntegration
import kombu.serialization
import sentry_sdk

from app import encoding


class ConfigVarRequiredError(Exception):
    pass


def getenv(key, default=None, conv=str, required=True):
    """If `default` is None, then the var is non-optional."""
    var = os.getenv(key, default)
    if var is None and required is True:
        raise ConfigVarRequiredError(
            f"Configuration variable '{key}' is required but was not provided."
        )
    elif var is not None:
        return conv(var)


def boolconv(s: str) -> bool:
    return s.lower() in ["true", "t", "yes"]


# Global logging level. Applies to any logger obtained through `app.reporting.get_logger`.
# https://docs.python.org/3/library/logging.html#logging-levels
LOG_LEVEL = getattr(logging, getenv("LOG_LEVEL", default="debug").upper())

# Switch for using loguru in place of the standard python logger.
USE_LOGURU = getenv("USE_LOGURU", default="False", conv=boolconv, required=False)

# Canonical name of the environment we're running in.
# e.g. dev, staging, production
ENVIRONMENT_ID = getenv("ENVIRONMENT_ID", default="unknown").lower()

# Connection string for Postgres.
# Postgres is used as the main database for the transaction matching system.
# https://www.postgresql.org/docs/10/static/libpq-connect.html#LIBPQ-CONNSTRING
POSTGRES_DSN = getenv("POSTGRES_DSN")

# Connection string for Redis.
# Redis is used as a configuration store that can be updated at runtime.
# https://redis-py.readthedocs.io/en/latest/#redis.StrictRedis.from_url
REDIS_DSN = getenv("REDIS_DSN")

# The prefix used on every Redis key.
REDIS_KEY_PREFIX = "txmatch"

# Connection string for InfluxDB.
# InfluxDB is used to store and report time-series statistics about the performance of the system.
# http://influxdb-python.readthedocs.io/en/latest/api-documentation.html#influxdb.InfluxDBClient.from_dsn
INFLUXDB_DSN = getenv("INFLUXDB_DSN", required=False)

# Sentry project data source name.
# https://docs.sentry.io/quickstart/#about-the-dsn
SENTRY_DSN = getenv("SENTRY_DSN", required=False)

if SENTRY_DSN is not None:
    sentry_sdk.init(
        dsn=SENTRY_DSN, environment=ENVIRONMENT_ID, integrations=[FlaskIntegration()]
    )

# AMQP Queue transport connection string.
# This is used by kombu to interact with the various queues used by transaction matching.
# http://docs.celeryproject.org/projects/kombu/en/latest/userguide/connections.html#urls
AMQP_DSN = getenv("AMQP_DSN")

# JSON encoding with custom extensions. Used in queue messages, postgres JSON field storage, et cetera.
JSON_SERIALIZER = "txmatch+json"

kombu.serialization.register(
    JSON_SERIALIZER,
    encoding.dumps,
    encoding.loads,
    content_type="application/txmatch+json",
    content_encoding="utf-8",
)
