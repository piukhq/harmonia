# Harmonia

[![pipeline status](https://git.bink.com/Olympus/harmonia/badges/develop/pipeline.svg)](https://git.bink.com/Olympus/harmonia/commits/develop) [![coverage report](https://git.bink.com/Olympus/harmonia/badges/develop/coverage.svg)](https://git.bink.com/Olympus/harmonia/commits/develop)

Transaction matching system. Goddess of harmony and accord. Daughter of Aphrodite.

## Table of Contents

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->


- [Prerequisites](#prerequisites)
- [Dependencies](#dependencies)
- [Project Setup](#project-setup)
    - [Database Schema](#database-schema)
    - [Development API Server](#development-api-server)
    - [Unit Tests](#unit-tests)
    - [End-to-End Matching Test](#end-to-end-matching-test)
        - [PostgreSQL](#postgresql)
        - [Redis](#redis)
        - [RabbitMQ](#rabbitmq)
- [Migrations](#migrations)
- [Deployment](#deployment)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

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

### Unit Tests

Testing is done with `pytest`.

To execute a full test run:

```bash
s/tests
```

### End-to-End Matching Test

There is a script provided that will run all the major components of the system in order. This should show a transaction going through the import->match process, and is useful for testing the interaction between the import stage and the matching worker.

To run the end-to-end script:

```bash
s/quick_work
```

This will destroy any existing docker containers with the names `postgres`, `redis`, or `rabbitmq`. It will then create new instances of these services, migrate the database, place some example transactions on the import queue, run the scheme & payment importers, then run the matching worker. The process is finished when you see a log line similar to the following:

```
2018-11-23 09:46:40,408 :: message-queue.export :: DEBUG :: Dumped data: {'matched_transaction_id': 1}. Publishing now.
```

At this point the matching worker can be closed (`KeyboardInterrupt` is handled cleanly.) The PostgreSQL, Redis, and RabbitMQ containers will be left as-is. You can inspect the state of these systems to see the side-effects of running the matching system.

#### PostgreSQL

```bash
docker exec -it postgres psql -U postgres

# this is not required, however it helps when viewing very wide tables
\x on

select * from payment_provider;
select * from loyalty_scheme;
select * from merchant_identifier;
select * from payment_transaction;
select * from scheme_transaction;
select * from matched_transaction;
```

Please note that no entry will have been made in the `import_transaction` table as the transactions were placed directly on the import queue, rather than being run through an import agent.

#### Redis

```bash
docker exec -it redis redis-cli

keys *
get txmatch:status:checkins:PaymentImportDirector
get txmatch:status:checkins:SchemeImportDirector
```

The `txmatch:status:checkins:*` keys contain timestamps from when various parts of the system were operating.

#### RabbitMQ

Navigate to http://localhost:15672 to see the RabbitMQ management dashboard. The default username and password is `guest`/`guest`.

If the system worked correctly, all txmatch queues should be empty save for the export queue, which should contain a single message. If you fetch this message, you should see a JSON payload containing the numeric ID of the MatchedTransaction to be exported.

## Migrations

[alembic](http://alembic.zzzcomputing.com/en/latest) is used for database schema migrations. The standard workflow for model changes is to use the autogenerate functionality to get a candidate migration, and then to manually inspect and edit where necessary.

A convenience script is provided in `s/makemigration` that will generate a new migration and test it by running it against a temporary database. This can be used as the first step in creating a new migration. Migrations created by this script should not be submitted as-is. _Note: in order to test the new migration, a new postgres container is created that is listening on port 5432. If you already have a postgres instance on this port, stop it before running the makemigration script._

Migrations should be manually squashed before each deployment for efficiency's sake. As a rule of thumb, each merge request should only include a single migration containing all the required changes for that feature. In some cases this will not be possible.

## Deployment

There is a Dockerfile provided in the project root. Build an image from this to get a deployment-ready version of the project.

## Development Tools

The Pipfile includes a few useful tools to aid project development.

### Loguru

Logs can be made more readable with the use of [loguru](https://github.com/Delgan/loguru) by setting `USE_LOGURU=true` in the `.env` file.

### Better Exceptions

Stack traces can be enchanced with [better-exceptions](https://github.com/Qix-/better-exceptions) by setting `BETTER_EXCEPTIONS=true` in the `.env` file.
