from pathlib import Path
import typing as t
import logging
import os

from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.rq import RqIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
import sentry_sdk


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

# Connection details for Postgres.
# Postgres is used as the main database for the transaction matching system.
POSTGRES_HOST = getenv("TXM_POSTGRES_HOST")
POSTGRES_PORT = getenv("TXM_POSTGRES_PORT", default="5432", conv=int)
POSTGRES_USER = getenv("TXM_POSTGRES_USER")
POSTGRES_PASS = getenv("TXM_POSTGRES_PASS", required=False)
POSTGRES_DB = getenv("TXM_POSTGRES_DB")

# This shouldn't need to be changed
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

# Connection details for Redis.
# Redis is used as a configuration store that can be updated at runtime.
REDIS_HOST = getenv("TXM_REDIS_HOST")
REDIS_PORT = getenv("TXM_REDIS_PORT", default="6379")
REDIS_USER = getenv("TXM_REDIS_USER", required=False)
REDIS_PASS = getenv("TXM_REDIS_PASS", required=False)
REDIS_DB = getenv("TXM_REDIS_DB", conv=int)
REDIS_URL = f"redis://:{REDIS_PASS}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# The prefix used on every Redis key.
REDIS_KEY_PREFIX = "txmatch"

# Connection details for RabbitMQ.
# These are only required for queue-based import agents.
RABBITMQ_USER = getenv("TXM_RABBITMQ_USER", required=False)
RABBITMQ_PASS = getenv("TXM_RABBITMQ_PASS", required=False)
RABBITMQ_HOST = getenv("TXM_RABBITMQ_HOST", required=False)
RABBITMQ_PORT = getenv("TXM_RABBITMQ_PORT", required=False, conv=int)
RABBITMQ_DSN = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT}//"

# Sentry project data source name.
# https://docs.sentry.io/quickstart/#about-the-dsn
SENTRY_DSN = getenv("TXM_SENTRY_DSN", required=False)

# Environment identifier to file issues under in Sentry.
SENTRY_ENV = getenv("TXM_SENTRY_ENV", default="unset").lower()

if SENTRY_DSN is not None:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENV,
        integrations=[FlaskIntegration(), RqIntegration(), RedisIntegration(), SqlalchemyIntegration()],
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

if not BLOB_STORAGE_DSN:
    # The path to load import files from.
    LOCAL_IMPORT_BASE_PATH = getenv("TXM_LOCAL_IMPORT_BASE_PATH", default="files", conv=Path)
else:
    LOCAL_IMPORT_BASE_PATH = None

# If set, export agents will not send data to external services:
# No transactions will be sent to merchant APIs.
# No requests will be sent to Atlas.
SIMULATE_EXPORTS = getenv("TXM_SIMULATE_EXPORTS", default="true", conv=boolconv)

# This dictionary is passed to `Flask.config.from_mapping`.
FLASK = dict(
    SECRET_KEY=b"{\xca\xb9\xf6F&\xe5\x9f\xaeq\xbb\xa0\x8a\x94\xce\xb2\xb7\x19\x8e\xaeY\xdb\xe6#\x8azF\x85y0w\x01"
)

# The prefix used on every API endpoint in the project.
URL_PREFIX = getenv("TXM_URL_PREFIX", default="/txm")

# Azure AD application details
AAD_TENANT_ID = getenv("TXM_AAD_TENANT_ID")
AAD_APPLICATION_URI = getenv("TXM_AAD_APPLICATION_URI", default="api://bink.com/harmonia")

# API key for service authentication.
SERVICE_API_KEY = "F616CE5C88744DD52DB628FAD8B3D"

# AES Cipher key.
AES_KEY = "6gZW4ARFINh4DR1uIzn12l7Mh1UF982L"

# Base URL for saving transaction export status.
ATLAS_URL = getenv("TXM_ATLAS_URL", required=False)

# Base URL for Merchant API configuration service.
EUROPA_URL = getenv("TXM_EUROPA_URL", required=False)

# Hashicorp Vault connection details
VAULT_URL = getenv("TXM_VAULT_URL", required=False)
VAULT_TOKEN = getenv("TXM_VAULT_TOKEN", required=False)
VAULT_KEY_PREFIX = getenv("TXM_VAULT_KEY_PREFIX", default="secret/harmonia")

# If set, visa files will be decrypted with GPG
VISA_ENCRYPTED = getenv("TXM_VISA_ENCRYPTED", default="true", conv=boolconv)

# Arguments to pass to gnupg.GPG(...)
GPG_ARGS = {
    "gpgbinary": getenv("TXM_GPG1_BINARY", default="gpg1"),
    "gnupghome": getenv("TXM_GPG_HOME", default="keyring"),
}
