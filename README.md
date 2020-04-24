# Harmonia

[![pipeline status](https://git.bink.com/Olympus/harmonia/badges/develop/pipeline.svg)](https://git.bink.com/Olympus/harmonia/commits/develop) [![coverage report](https://git.bink.com/Olympus/harmonia/badges/develop/coverage.svg)](https://git.bink.com/Olympus/harmonia/commits/develop)

Transaction matching system. Goddess of harmony and accord. Daughter of Aphrodite.

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Harmonia](#harmonia)
  - [Prerequisites](#prerequisites)
  - [Dependencies](#dependencies)
  - [Project Setup](#project-setup)
    - [MacOS Dependencies](#macos-dependencies)
    - [Virtual Environment](#virtual-environment)
    - [Database Schema Migration](#database-schema-migration)
    - [Development API Server](#development-api-server)
    - [Unit Tests](#unit-tests)
    - [End-to-End Matching Test](#end-to-end-matching-test)
      - [Testing with Flexible Transactions](#testing-with-flexible-transactions)
      - [Testing Visa](#testing-visa)
      - [Inspecting PostgreSQL](#inspecting-postgresql)
      - [Inspecting Redis](#inspecting-redis)
  - [Migrations](#migrations)
  - [Deployment](#deployment)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Prerequisites

- [pipenv](https://docs.pipenv.org)

## Dependencies

The following is a list of the important dependencies used in the project. You do not need to install these manually. See [project setup](#project-setup) for installation instructions.

- [SQLAlchemy](https://www.sqlalchemy.org) - Object-relational mapping library. Used for interacting with PostgreSQL.
- [Alembic](http://alembic.zzzcomputing.com/en/latest) - SQLAlchemy migration library.
- [Flask](http://flask.pocoo.org) - API framework.
- [Sentry SDK](https://docs.sentry.io/quickstart?platform=python) - Client for the Sentry error reporting platform. Includes Flask integration.
- [Click](http://click.pocoo.org/6) - Used for building the management CLI for each part of the system.
- [Redis](https://redis-py.readthedocs.io/en/latest) - Key-value store used for storing system configuration and task queues.
- [APScheduler](https://apscheduler.readthedocs.io/en/latest) - Used for scheduling various time-based parts of the system.
- [Marshmallow](https://marshmallow.readthedocs.io/en/latest) - (De)serialization library for converting between JSON payloads and database objects.
- [RQ](https://python-rq.org) - Redis-based task queue. Most transaction matching processes run as RQ jobs.

## Project Setup

Pipenv is used for managing project dependencies and execution.

### MacOS Dependencies

Before installing the project dependencies on MacOS, you will need to install a few homebrew dependencies, and let the system know where to find the OpenSSL libraries.

```bash
brew install postgres openssl
export LDFLAGS="-L/usr/local/opt/openssl/lib"
```

### Virtual Environment

To create a virtualenv and install required software packages:

```bash
pipenv install --dev
```

Project configuration is done through environment variables. A convenient way to set these is in a `.env` file in the project root. This file will be sourced by Pipenv when `pipenv run` and `pipenv shell` are used. See `settings.py` for configuration options that can be set in this file.

All transaction matching environment variables are prefixed with `TXM_`.

To make a `.env` file from the provided example:

```bash
cp .env.example .env
```

The provided example is sufficient as a basic configuration, but modification may be required for specific use-cases.

The `.env` file contains connection parameters for the two major services used in the project; PostgreSQL and Redis. The default connection parameters assume a local instance of these services listening on ports 51234 (PostgreSQL) and 61234 (Redis.)

To quickly create docker containers for the required services:

```bash
s/services
```

### Database Schema Migration

If you used the `s/services` script then you can skip this step.

Once PostgreSQL is running, you will need to create all the tables and indices required by the project.

To apply all migrations:

```bash
s/migrate
```

### Development API Server

The flask development server is used for running the project locally. This should be replaced with a WSGI-compatible server for deployment to a live environment.

To run the flask development server:

```bash
s/api
```

You may see the following output in the flask server logs:

```bash
Tip: There are .env files present. Do "pip install python-dotenv" to use them.
```

This can safely be ignored; pipenv is loading the `.env` variables.

### Unit Tests

Testing is done with `pytest`.

To execute a full test run:

```bash
s/test
```

### End-to-End Matching Test

You can test matching by running the end-to-end test harness.

```bash
s/test-end-to-end
```

By default this will test a few transactions going through the system with the `bink-loyalty` loyalty scheme and the `bink-payment` payment provider. If you want to change the parameters used for the test, you can create a TOML file containing the fixture.

```bash
cp harness/fixtures/default.toml my-fixture.toml

...
edit my-fixture.toml with the changes you want to make
...

s/test-end-to-end -f my-fixture.toml
```

#### Testing with Flexible Transactions
The default TOML file will test the happy path by generating a transaction for both the loyalty scheme and the payment scheme. There are cases where this may not be ideal, and the payment transaction and loyalty transaction will require some differences in order to test some matching functionality. For example, an agent may have fallback matching criteria in case multiple transactions are returned for the same amount and date e.g filtering by card number.

For these scenarios, it is possible to configure separate transactions for the loyalty scheme and the payment provider.

Example:

```TOML
# Transactions only imported as payment transactions
[[payment_provider.transactions]]
date = 2020-06-02T15:46:30Z  # Datetime representing the transaction time
amount = 1222  # Transaction amount in pennies
points = 8  # Points awarded for transaction

# Settlement key of the payment transaction - should be kept to 9 chars or less for Mastercard
settlement_key = "1111111111"
token = "1111"  # Payment token

# Which user to link the payment to - does not need to be changed in most cases as there is not much need to test with more than one user.
user_id = 0  

# Transactions only imported as scheme transactions
[[loyalty_scheme.transactions]]
date = 2020-06-02T15:47:45Z
amount = 1222
points = 8
first_six = "123456"  # Payment card first six
last_four = "7890"  # Payment card last four
```

#### Testing Visa

If you want to test with a Visa import file, you will need to have gpg1 installed on your system. You will also need to be running Hashicorp Vault on port 8200.

Example:

```bash
brew install gpg1
docker run -d --name vault -p 8200:8200 vault
docker logs vault  # look for the vault token near the beginning of the logs
echo 'VAULT_TOKEN=your_vault_token_goes_here >> .env'
s/test-end-to-end -f my-visa-fixture.toml
```

After running these tests, the PostgreSQL and Redis containers will be left intact for manual data inspection.

#### Inspecting PostgreSQL

```bash
s/psql

select * from payment_provider;
select * from loyalty_scheme;
select * from merchant_identifier;
select * from import_transaction;
select * from payment_transaction;
select * from scheme_transaction;
select * from matched_transaction;
select * from export_transaction;
```

#### Inspecting Redis

```bash
docker exec -it txm-redis redis-cli

keys *
get txmatch:status:checkins:PaymentImportDirector
get txmatch:status:checkins:SchemeImportDirector
```

The `txmatch:status:checkins:*` keys contain timestamps from when various parts of the system were operating.

## Migrations

[alembic](http://alembic.zzzcomputing.com/en/latest) is used for database schema migrations. The standard workflow for model changes is to use the autogenerate functionality to get a candidate migration, and then to manually inspect and edit where necessary.

Migrations should be manually squashed before each deployment for efficiency's sake. As a rule of thumb, each merge request should only include a single migration containing all the required changes for that feature. In some cases this will not be possible.

## Deployment

There is a Dockerfile provided in the project root. Build an image from this to get a deployment-ready version of the project.
