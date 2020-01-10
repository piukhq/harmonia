from pathlib import Path
import typing as t
import logging
import os

from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.rq import RqIntegration
import sentry_sdk

from environment import read_env


read_env()


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


def boolconv(s: str) -> bool:
    return s.lower() in ["true", "t", "yes"]


# Global logging level.
# Applies to any logger obtained through `app.reporting.get_logger`.
# https://docs.python.org/3/library/logging.html#logging-levels
LOG_LEVEL = getattr(logging, getenv("TXM_LOG_LEVEL", default="debug").upper())

# Debug mode toggle. Running in debug mode disables a lot of error handling.
DEBUG = getenv("TXM_DEBUG", default="false", conv=boolconv)

# Canonical name of the environment we're running in.
# e.g. dev, staging, production
ENVIRONMENT_ID = getenv("TXM_ENVIRONMENT_ID", default="unknown").lower()

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

# Sentry project data source name.
# https://docs.sentry.io/quickstart/#about-the-dsn
SENTRY_DSN = getenv("TXM_SENTRY_DSN", required=False)

if SENTRY_DSN is not None:
    sentry_sdk.init(dsn=SENTRY_DSN, environment=ENVIRONMENT_ID, integrations=[FlaskIntegration(), RqIntegration()])

# JSON encoding with custom extensions.
# Used in queue messages, postgres JSON field storage, et cetera.
JSON_SERIALIZER = "txmatch+json"

# Base URL for the Hermes API
HERMES_URL = getenv("TXM_HERMES_URL")

# If set, file-based import agents will talk with blob storage instead.
USE_BLOB_STORAGE = getenv("TXM_USE_BLOB_STORAGE", default="false", conv=boolconv)

if USE_BLOB_STORAGE:
    # Azure Blob Storage account details.
    BLOB_ACCOUNT_NAME = getenv("TXM_BLOB_ACCOUNT_NAME")
    BLOB_ACCOUNT_KEY = getenv("TXM_BLOB_ACCOUNT_KEY")
else:
    # The path to load import files from.
    LOCAL_IMPORT_BASE_PATH = getenv("TXM_LOCAL_IMPORT_BASE_PATH", default="files", conv=Path)

# This dictionary is passed to `Flask.config.from_mapping`.
FLASK = dict(
    SECRET_KEY=(b"{\xca\xb9\xf6F&\xe5\x9f\xaeq\xbb\xa0\x8a\x94\xce\xb2\xb7\x19\x8e\xaeY\xdb\xe6#\x8azF\x85y0w\x01")
)

# The prefix used on every API endpoint in the project.
URL_PREFIX = getenv("TXM_URL_PREFIX", default="/txm")

# API key for service authentication.
SERVICE_API_KEY = "F616CE5C88744DD52DB628FAD8B3D"

# AES Cipher key.
AES_KEY = "6gZW4ARFINh4DR1uIzn12l7Mh1UF982L"

# Base URL for saving transaction export status.
ATLAS_URL = getenv("TXM_ATLAS_URL", required=False)
