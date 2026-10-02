#!/bin/sh
# Aplica el bootstrap PMV1 contra un Postgres ya en ejecución (p. ej. contenedor huérfano sin auth_db).
# Uso desde la raíz del repo:
#   docker run --rm --network siprim_default \
#     -v "%CD%/database:/opt/siprim/database:ro" \
#     -e PGHOST=siprim-postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
#     postgres:16-alpine sh /opt/siprim/database/bootstrap_remoto.sh
set -eu

ROOT=/opt/siprim/database
export PGPASSWORD="${POSTGRES_PASSWORD:-postgres}"
PGHOST="${PGHOST:-localhost}"
H="-h $PGHOST"

create_role() {
  role="$1"
  password="$2"
  if ! psql $H -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
      --tuples-only --command "SELECT 1 FROM pg_roles WHERE rolname = '$role'" | grep -q 1; then
    psql $H -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
      --command "CREATE ROLE $role LOGIN PASSWORD '$password'"
  fi
}

create_database() {
  database="$1"
  owner="$2"
  if ! psql $H -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
      --tuples-only --command "SELECT 1 FROM pg_database WHERE datname = '$database'" | grep -q 1; then
    createdb $H --username "$POSTGRES_USER" --owner "$owner" "$database"
  fi
}

apply_folder() {
  database="$1"
  folder="$2"
  owner="$3"
  for file in "$ROOT/$folder"/*.sql; do
    [ -f "$file" ] || continue
    psql $H -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$database" \
      --command "SET ROLE $owner" --file "$file"
  done
}

create_role auth_app auth_dev_only
create_role platform_app platform_dev_only
create_role economic_app economic_dev_only

create_database auth_db auth_app
create_database platform_db platform_app
create_database economic_db economic_app

apply_folder auth_db auth_db auth_app
apply_folder platform_db platform_db platform_app
apply_folder economic_db economic_db economic_app

psql $H -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname auth_db \
  --file "$ROOT/permisos/01_auth_db.sql"
psql $H -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname platform_db \
  --file "$ROOT/permisos/02_platform_db.sql"
psql $H -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname economic_db \
  --file "$ROOT/permisos/03_economic_db.sql"

echo "Bootstrap PMV1 remoto completado (auth_db, platform_db, economic_db)."
