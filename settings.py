import logging
import os
import typing as t
from pathlib import Path

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.rq import RqIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.scrubber import DEFAULT_DENYLIST, EventScrubber


class ConfigVarRequiredError(Exception):
    pass


def getenv(key: str, default: str = None, conv: t.Callable = str, required: bool = True) -> t.Any:
    """If `default` is None, then the var is non-optional."""
    var = os.getenv(key, default)
    if var is None and required is True:
        raise ConfigVarRequiredError(f"Configuration variable '{key}' is required but was not provided.")
    elif var is not None:
        return conv(var)
    else:
        return None


def delimited_list_conv(s: str, *, sep: str = ",") -> t.List[str]:
    return [_.strip() for _ in s.split(sep) if _]


def boolconv(s: str) -> bool:
    return s.lower() in ["true", "t", "yes"]


# Global logging level.
# Applies to any logger obtained through `app.reporting.get_logger`.
# https://docs.python.org/3/library/logging.html#logging-levels
LOG_LEVEL = getattr(logging, getenv("TXM_LOG_LEVEL", default="debug").upper())

# If enabled, logs will be emitted as JSON objects.
# If DEVELOPMENT mode is enabled, this emits formatted & highlighted python objects instead.
LOG_JSON = getenv("TXM_LOG_JSON", default="true", conv=boolconv)

# Global query tracing level.
# 0 = No query tracing.
# 1 = Trace query descriptions from `db.run_query`.
# 2 = Dump full query SQL. This is very noisy, only useful for the most granular of debugging tasks.
QUERY_TRACE_LEVEL = getenv("TXM_QUERY_TRACE_LEVEL", default="0", conv=int)

# These are set automatically based on the above.
TRACE_QUERY_DESCRIPTIONS = QUERY_TRACE_LEVEL > 0
TRACE_QUERY_SQL = QUERY_TRACE_LEVEL > 1

# Debug mode toggle. Running in debug mode disables a lot of error handling.
DEBUG = getenv("TXM_DEBUG", default="false", conv=boolconv)

# Development mode toggle. Adds extra functionality for local development work.
DEVELOPMENT = getenv("TXM_DEVELOPMENT", default="false", conv=boolconv)

# This shouldn't need to be changed
if getenv("TXM_POSTGRES_URI", required=False):
    POSTGRES_DSN = getenv("TXM_POSTGRES_URI")
else:
    # Connection details for Postgres.
    # Postgres is used as the main database for the transaction matching system.
    POSTGRES_HOST = getenv("TXM_POSTGRES_HOST")
    POSTGRES_PORT = getenv("TXM_POSTGRES_PORT", default="5432", conv=int)
    POSTGRES_USER = getenv("TXM_POSTGRES_USER")
    POSTGRES_PASS = getenv("TXM_POSTGRES_PASS", required=False)
    POSTGRES_DB = getenv("TXM_POSTGRES_DB")

    POSTGRES_DSN = "".join(
        [
            "postgresql+psycopg2://",
            POSTGRES_USER,
            f":{POSTGRES_PASS}" if POSTGRES_PASS else "",
            "@",
            POSTGRES_HOST,
            ":",
            str(POSTGRES_PORT),
            "/",
            POSTGRES_DB,
        ]
    )

POSTGRES_CONNECT_ARGS = {"application_name": "harmonia"}

# Connection details for Redis.
# Redis is used as a configuration store that can be updated at runtime.
REDIS_URL = getenv("TXM_REDIS_URL")

# The prefix used on every Redis key.
REDIS_KEY_PREFIX = "txmatch"

# Connection details for RabbitMQ.
# These are only required for queue-based import agents.
RABBITMQ_DSN = getenv("TXM_AMQP_DSN", "amqp://guest:guest@localhost:5672//")

# Sentry project data source name.
# https://docs.sentry.io/quickstart/#about-the-dsn
SENTRY_DSN = getenv("TXM_SENTRY_DSN", required=False)

# Environment identifier to file issues under in Sentry.
SENTRY_ENV = getenv("TXM_SENTRY_ENV", default="unset").lower()
SENTRY_SAMPLE_RATE = getenv("SENTRY_SAMPLE_RATE", default="0.0", conv=float)

if SENTRY_DSN is not None:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENV,
        integrations=[FlaskIntegration(), RqIntegration(), RedisIntegration(), SqlalchemyIntegration()],
        traces_sample_rate=SENTRY_SAMPLE_RATE,
        event_scrubber=EventScrubber(denylist=DEFAULT_DENYLIST + ["body"]),
    )

# JSON encoding with custom extensions.
# Used in queue messages, postgres JSON field storage, et cetera.
JSON_SERIALIZER = "txmatch+json"

# Base URL for the Hermes API
HERMES_URL = getenv("TXM_HERMES_URL", required=False)

# If the scheme exists in this list, use HERMES_SLUG_FORMAT_STRING as below
HERMES_SLUGS_TO_FORMAT = getenv("TXM_HERMES_SLUGS_TO_FORMAT", default="", conv=delimited_list_conv)

# If set, format the scheme slug with this string before sending to Hermes.
# This allows things such as adding `-mock` to the end of a scheme slug in dev.
HERMES_SLUG_FORMAT_STRING = getenv("TXM_HERMES_SLUG_FORMAT_STRING", required=False)

# If set, file-based import agents will talk with blob storage instead.
BLOB_STORAGE_DSN = getenv("TXM_BLOB_STORAGE_DSN", required=False)
BLOB_IMPORT_CONTAINER = getenv("TXM_BLOB_IMPORT_CONTAINER", default="harmonia-imports")
BLOB_ARCHIVE_CONTAINER = getenv("TXM_BLOB_ARCHIVE_CONTAINER", default="harmonia-archive")
BLOB_EXPORT_CONTAINER = getenv("TXM_BLOB_EXPORT_CONTAINER", default="harmonia-exports")
BLOB_AUDIT_CONTAINER = getenv("TXM_BLOB_AUDIT_CONTAINER", default="harmonia-atlas")

if not BLOB_STORAGE_DSN:
    # The path to load import files from.
    LOCAL_IMPORT_BASE_PATH = getenv("TXM_LOCAL_IMPORT_BASE_PATH", default="files", conv=Path)
else:
    LOCAL_IMPORT_BASE_PATH = None

# If set, messages will be queued for Atlas and data warehouse consumption.
AUDIT_EXPORTS = getenv("TXM_AUDIT_EXPORTS", default="true", conv=boolconv)

# This dictionary is passed to `Flask.config.from_mapping`.
FLASK = dict(
    SECRET_KEY=b"{\xca\xb9\xf6F&\xe5\x9f\xaeq\xbb\xa0\x8a\x94\xce\xb2\xb7\x19\x8e\xaeY\xdb\xe6#\x8azF\x85y0w\x01"
)

# The prefix used on every API endpoint in the project.
URL_PREFIX = getenv("TXM_URL_PREFIX", default="/txm")

# API key for service authentication.
SERVICE_API_KEY = "F616CE5C88744DD52DB628FAD8B3D"

# Base URL for Merchant API configuration service.
EUROPA_URL = getenv("TXM_EUROPA_URL", required=False)

# Mount point for KeyVault secrets. For local dev you will want to change this.
SECRETS_DIR = getenv("TXM_SECRETS_DIR", default="/mnt/secrets")

# Prometheus settings
PROMETHEUS_PUSH_GATEWAY = getenv("TXM_PROMETHEUS_PUSH_GATEWAY", default="http://localhost:9100")
PUSH_PROMETHEUS_METRICS = getenv("TXM_PUSH_PROMETHEUS_METRICS", default="true", conv=boolconv)
PROMETHEUS_SEND_PID = getenv("TXM_PROMETHEUS_SEND_PID", default="true", conv=boolconv)
PROMETHEUS_JOB = "harmonia"

# Management API settings
API_AUTH_ENABLED = getenv("TXM_API_AUTH_ENABLED", default="true", conv=boolconv)

# Azure AD application details
AAD_TENANT_ID = getenv("TXM_AAD_TENANT_ID", required=API_AUTH_ENABLED)
AAD_APPLICATION_URI = getenv("TXM_AAD_APPLICATION_URI", default="api://bink.com/harmonia")
SECRETS_PATH = getenv("SECRETS_PATH", default="/mnt/secrets")
