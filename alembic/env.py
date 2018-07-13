from __future__ import with_statement
from logging.config import fileConfig
import sys
import os

from alembic import context
from sqlalchemy import create_engine

sys.path.append(os.getcwd())

from app.db import Base  # noqa
from app.models import *  # noqa
import settings  # noqa

# setup default sqlalchemy configuration (loggers et cetera.)
fileConfig(context.config.config_file_name)

# custom declarative base metadata used in both migration methods below.
target_metadata = Base.metadata


def run_migrations_offline():
    url = settings.POSTGRES_DSN
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = create_engine(settings.POSTGRES_DSN)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
