#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# create users and databases
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
	CREATE USER harmonia;
	CREATE DATABASE harmonia;
    ALTER DATABASE harmonia OWNER TO harmonia;

	CREATE USER api_reflector;
	CREATE DATABASE api_reflector;
    ALTER DATABASE api_reflector OWNER TO api_reflector;
EOSQL

# create tables and load fixtures
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "api_reflector" < /usr/local/fixtures/api_reflector.sql
