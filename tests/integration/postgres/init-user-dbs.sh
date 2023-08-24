#!/bin/bash
set -euo pipefail
IFS=$'\n\t'
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
	CREATE USER harmonia;
	CREATE DATABASE harmonia;
    ALTER DATABASE harmonia OWNER TO harmonia;

	CREATE USER api_reflector;
	CREATE DATABASE api_reflector;
    ALTER DATABASE api_reflector OWNER TO api_reflector;
EOSQL

# GRANT ALL PRIVILEGES ON DATABASE harmonia TO harmonia;
# GRANT ALL PRIVILEGES ON DATABASE api_reflector TO api_reflector;
