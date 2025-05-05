#!/bin/bash
set -e

# Create the sports_league_owner role with the specified password
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'sports_league_owner') THEN
            CREATE ROLE sports_league_owner WITH LOGIN PASSWORD '$POSTGRES_PASSWORD';
        END IF;
    END
    \$\$;
"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "
    ALTER ROLE sports_league_owner WITH SUPERUSER;
    ALTER DATABASE $POSTGRES_DB OWNER TO sports_league_owner;
    GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO sports_league_owner;
"

# Set search_path for the database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "
    ALTER DATABASE $POSTGRES_DB SET search_path TO public;
" 