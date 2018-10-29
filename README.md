# Harmonia

[![pipeline status](https://git.bink.com/Olympus/harmonia/badges/develop/pipeline.svg)](https://git.bink.com/Olympus/harmonia/commits/develop) [![coverage report](https://git.bink.com/Olympus/harmonia/badges/develop/coverage.svg)](https://git.bink.com/Olympus/harmonia/commits/develop)

Transaction matching system. Goddess of harmony and accord. Daughter of Aphrodite.

## Prerequisites

* [pipenv](https://docs.pipenv.org)

## Dependencies

The following is a list of the important dependencies used in the project. You do not need to install these manually. See [local development](#local-development) for installation instructions.

* [SQLAlchemy](https://www.sqlalchemy.org) - Object-relational mapping library. Used for interacting with PostgreSQL.
* [Alembic](http://alembic.zzzcomputing.com/en/latest) - SQLAlchemy migration library.
* [Flask](http://flask.pocoo.org) - API framework.
* [InfluxDB](http://influxdb-python.readthedocs.io/en/latest) - Time-series database used for logging performance metrics.
* [Sentry SDK](https://docs.sentry.io/quickstart?platform=python) - Client for the Sentry error reporting platform. Includes Flask integration.
* [Click](http://click.pocoo.org/6) - Used for building the management CLI for each part of the system.
* [Redis](https://redis-py.readthedocs.io/en/latest) - Key-value store used for storing system configuration.
* [APScheduler](https://apscheduler.readthedocs.io/en/latest) - Used for scheduling various time-based parts of the system.

## Local Development

1. Install requirements.

```bash
pipenv install --dev
```

2. Create `.env` file. See `settings.py` for settings that must be or can be set in here. You should also set the `FLASK_ENV` and `FLASK_DEBUG` variables if you want to run the flask server.

```
FLASK_APP = app.api:app
FLASK_ENV = development
FLASK_DEBUG = true

... additional settings go here ...
```

3. Run migrations

```bash
pipenv run alembic upgrade head
```

4. Run the tests

```bash
pipenv run pytest
```

You can use pytest-cov if you wish to see test coverage.

```bash
pipenv run pytest --cov app
```

## Local API Server

You can use the Flask development server for manual testing of the API.

```bash
pipenv run flask run
```

You may see the following output in the flask server logs:

```
Tip: There are .env files present. Do "pip install python-dotenv" to use them.
```

This can safely be ignored. `pipenv` is loading our `.env` variables for us.

## Migrations

[alembic](http://alembic.zzzcomputing.com/en/latest) is used for database schema migrations. The standard workflow for model changes is to use the autogenerate functionality to get a candidate migration, and then to manually inspect and edit where necessary.

Migrations should be manually squashed before each deployment for efficiency's sake. As a rule of thumb, each merge request should only include a single migration containing all the required changes for that feature. In some cases this will not be possible.

## Tests

```bash
pipenv install -e .
pipenv shell
```

## Deployment

```bash
pipenv install --system --deploy .
```
