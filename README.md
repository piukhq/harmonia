# Harmonia

[![pipeline status](https://git.bink.com/Olympus/harmonia/badges/develop/pipeline.svg)](https://git.bink.com/Olympus/harmonia/commits/develop) [![coverage report](https://git.bink.com/Olympus/harmonia/badges/develop/coverage.svg)](https://git.bink.com/Olympus/harmonia/commits/develop)

Transaction matching system. Goddess of harmony and accord. Daughter of Aphrodite.

## Prerequisites

* [pipenv](https://docs.pipenv.org)

## Dependencies

The following is a list of the important dependencies used in the project. You do not need to install these manually. See [project setup](#project-setup) for installation instructions.

* [SQLAlchemy](https://www.sqlalchemy.org) - Object-relational mapping library. Used for interacting with PostgreSQL.
* [Alembic](http://alembic.zzzcomputing.com/en/latest) - SQLAlchemy migration library.
* [Flask](http://flask.pocoo.org) - API framework.
* [InfluxDB](http://influxdb-python.readthedocs.io/en/latest) - Time-series database used for logging performance metrics.
* [Sentry SDK](https://docs.sentry.io/quickstart?platform=python) - Client for the Sentry error reporting platform. Includes Flask integration.
* [Click](http://click.pocoo.org/6) - Used for building the management CLI for each part of the system.
* [Redis](https://redis-py.readthedocs.io/en/latest) - Key-value store used for storing system configuration.
* [APScheduler](https://apscheduler.readthedocs.io/en/latest) - Used for scheduling various time-based parts of the system.

## Project Setup

Pipenv is used for managing project dependencies and execution.

To create a virtualenv and install required software packages:

```bash
pipenv install --dev
```

Project configuration is done through environment variables. A convenient way to set these is in a `.env` file in the project root. This file will be sourced by Pipenv when `pipenv run` and `pipenv shell` are used. See `settings.py` for configuration options that can be set in this file.

To make a `.env` file from the provided example:

```bash
cp .env.example .env
```

The provided example is sufficient as a basic configuration, but modification may be required for specific use-cases.

The `.env` file contains connection strings for the three major services used in the project; PostgreSQL, RabbitMQ, and Redis. These connection strings assume a local instance of these services listening on the default ports.

To quickly create docker containers for the required services:

```bash
s/services
```

### Database Schema

Once previous steps have been completed, you will need to create all the tables and indices required by the project.

To apply all migrations:

```bash
s/migrate
```

### Unit Tests

Testing is done with `pytest`.

To execute a full test run:

```bash
s/tests
```

### Development API Server

The flask development server is used for running the project locally. This should be replaced with a WSGI-compatible server for deployment to a live environment.

To run the flask development server:

```bash
s/serve
```

You may see the following output in the flask server logs:

```
Tip: There are .env files present. Do "pip install python-dotenv" to use them.
```

This can safely be ignored; pipenv is loading the `.env` variables.

## Migrations

[alembic](http://alembic.zzzcomputing.com/en/latest) is used for database schema migrations. The standard workflow for model changes is to use the autogenerate functionality to get a candidate migration, and then to manually inspect and edit where necessary.

A convenience script is provided in `s/makemigration` that will generate a new migration and test it by running it against a temporary database. This can be used as the first step in creating a new migration. Migrations created by this script should not be submitted as-is. _Note: in order to test the new migration, a new postgres container is created that is listening on port 5432. If you already have a postgres instance on this port, stop it before running the makemigration script._

Migrations should be manually squashed before each deployment for efficiency's sake. As a rule of thumb, each merge request should only include a single migration containing all the required changes for that feature. In some cases this will not be possible.

## Deployment

There is a Dockerfile provided in the project root. Build an image from this to get a deployment-ready version of the project.
