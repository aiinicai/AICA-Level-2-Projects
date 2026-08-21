#!/usr/bin/env sh
set -eu

if [ -z "${POSTGRES_APP_PASSWORD:-}" ]; then
  printf '%s\n' "POSTGRES_APP_PASSWORD is required." >&2
  exit 1
fi

psql --set=ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --set=db_name="$POSTGRES_DB" \
  --set=app_user="practice_app" \
  --set=app_password="$POSTGRES_APP_PASSWORD" <<-'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'app_user', :'app_password')
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = :'app_user') \gexec
GRANT CONNECT ON DATABASE :"db_name" TO :"app_user";
SQL
