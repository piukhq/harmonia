# Harmonia

[![pipeline status](https://git.bink.com/Olympus/harmonia/badges/develop/pipeline.svg)](https://git.bink.com/Olympus/harmonia/commits/develop) [![coverage report](https://git.bink.com/Olympus/harmonia/badges/develop/coverage.svg)](https://git.bink.com/Olympus/harmonia/commits/develop)

Transaction matching system. Goddess of harmony and accord. Daughter of Aphrodite.

## Table of Contents

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
<!-- END doctoc generated TOC please keep comment here to allow auto update -->

- [Prerequisites](#prerequisites)
- [Dependencies](#dependencies)
- [Project Setup](#project-setup)
    - [Database Schema](#database-schema)
    - [Development API Server](#development-api-server)
    - [Unit Tests](#unit-tests)
    - [End-to-End Matching Test](#end-to-end-matching-test)
        - [PostgreSQL](#postgresql)
        - [Redis](#redis)
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
* [Sentry SDK](https://docs.sentry.io/quickstart?platform=python) - Client for the Sentry error reporting platform. Includes Flask integration.
* [Click](http://click.pocoo.org/6) - Used for building the management CLI for each part of the system.
* [Redis](https://redis-py.readthedocs.io/en/latest) - Key-value store used for storing system configuration and task queues.
* [APScheduler](https://apscheduler.readthedocs.io/en/latest) - Used for scheduling various time-based parts of the system.
* [Marshmallow](https://marshmallow.readthedocs.io/en/latest) - (De)serialization library for converting between JSON payloads and database objects.
* [RQ](https://python-rq.org) - Redis-based task queue. Most transaction matching processes run as RQ jobs.

## Project Setup

Pipenv is used for managing project dependencies and execution.

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

The `.env` file contains connection strings for the two major services used in the project; PostgreSQL and Redis. These connection strings assume a local instance of these services listening on the default ports.

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

Both the transaction file production script (`s/producer.py`) and the import agents will expect their respective import directories to already exist. By default they will look for files in `./files/imports/SLUG/*`.

To make the required import directories:

```bash
mkdir -p files/imports/{example-loyalty-scheme,example-payment-provider}
```

Before running the end-to-end script, you must have a copy of the Hermes project on your machine with a valid database, and have the server running on port 8000.

Example of a valid Hermes setup:

```bash
git clone git@git.bink.com:Olympus/hermes.git ~/hermes
cd ~/hermes
docker run -d -p 5432:5432 postgres:latest
echo -e "HERMES_DATABASE_HOST=localhost\nHERMES_DATABASE_NAME=postgres" > .env
python3 -m venv ~/.virtualenvs/hermes
. ~/.virtualenvs/hermes/bin/activate
pip install -r requirements.txt
./manage.py migrate
./manage.py runserver
```

After setting Hermes up, modify `s/quick_work` and set the variables `HERMES_PATH` and `HERMES_PY` to the correct values.

Note: As part of running the end-to-end test, we need to add a payment card account to Hermes. Usually this relies on Metis being available to enrol the card. You can set this up locally along with Pelops as a mock API for Metis to use instead of Spreedly, however for simplicity's sake I recommend just removing the code in Hermes that makes the call to Metis. A potential mitigation for this issue would be to update Hermes so that it does not call Metis when it's running in LOCAL mode.

Here is a diff that removes the metis calls from Hermes at the time of writing:

```diff
diff --git a/payment_card/views.py b/payment_card/views.py
index e9cbc54..946067c 100644
--- a/payment_card/views.py
+++ b/payment_card/views.py
@@ -15,7 +15,7 @@ from rest_framework.generics import GenericAPIView, RetrieveUpdateDestroyAPIView
 from rest_framework.response import Response
 from rest_framework.views import APIView

-from payment_card import metis, serializers
+from payment_card import serializers
 from payment_card.forms import CSVUploadForm
 from payment_card.models import PaymentCard, PaymentCardAccount, PaymentCardAccountImage, ProviderStatusMapping
 from payment_card.serializers import PaymentCardClientSerializer
@@ -171,7 +171,6 @@ class ListCreatePaymentCardAccount(APIView):
                 return ListCreatePaymentCardAccount.supercede_old_card(account, old_account, user)
         account.save()
         PaymentCardAccountEntry.objects.create(user=user, payment_card_account=account)
-        metis.enrol_new_payment_card(account)
         return account

     @staticmethod
@@ -190,7 +189,6 @@ class ListCreatePaymentCardAccount(APIView):
         if old_account.is_deleted:
             account.save()
             PaymentCardAccountEntry.objects.create(user=user, payment_card_account=account)
-            metis.enrol_existing_payment_card(account)
         else:
             account.status = old_account.status
             account.save()
```

To run the end-to-end script:

```bash
s/quick_work
```

This will destroy any existing docker containers with the name `txm-postgres` or `txm-redis`. It will then create new instances of these services, migrate the database, and run each stage of the transaction import, matching, and export process.

When everything is finished, the PostgreSQL and Redis containers will be left as-is. You can inspect the state of these systems to see the side-effects of running the matching system.

#### PostgreSQL

```bash
docker exec -it txm-postgres psql -U postgres

# this is not required, however it helps when viewing very wide tables
\x on

select * from payment_provider;
select * from loyalty_scheme;
select * from merchant_identifier;
select * from import_transaction;
select * from payment_transaction;
select * from scheme_transaction;
select * from matched_transaction;
select * from export_transaction;
```

#### Redis

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
