#!/usr/bin/env sh
set -eu

action="${1:-migrate}"
argument="${2:-}"
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repository_root=$(CDPATH= cd -- "$script_dir/../.." && pwd)
cd "$repository_root"

if [ ! -f .env ]; then
  printf '%s\n' "Missing .env. Run ./deploy/scripts/practice.sh start first." >&2
  exit 1
fi

compose() {
  docker compose --env-file .env -f deploy/compose/compose.yml "$@"
}

case "$action" in
  migrate)
    compose run --rm --build migrate
    ;;
  backup)
    database_name=$(compose exec -T database printenv POSTGRES_DB | tr -d '\r')
    backup_path="${argument:-backups/practice-management-$(date -u +%Y%m%dT%H%M%SZ).dump}"
    mkdir -p "$(dirname -- "$backup_path")"
    compose exec -T database pg_dump --username practice_migrator --dbname "$database_name" \
      --format=custom --file=/tmp/practice-management.dump
    database_container=$(compose ps -q database)
    docker cp "$database_container:/tmp/practice-management.dump" "$backup_path"
    compose exec -T database rm -f /tmp/practice-management.dump
    printf '%s\n' "Backup created: $backup_path"
    ;;
  verify-backup)
    if [ -z "$argument" ] || [ ! -f "$argument" ]; then
      printf '%s\n' "Usage: $0 verify-backup <backup.dump>" >&2
      exit 2
    fi
    database_container=$(compose ps -q database)
    docker cp "$argument" "$database_container:/tmp/practice-restore-verification.dump"
    compose exec -T database dropdb --username practice_migrator --if-exists practice_restore_verification
    compose exec -T database createdb --username practice_migrator practice_restore_verification
    compose exec -T database pg_restore --username practice_migrator --dbname practice_restore_verification \
      --exit-on-error /tmp/practice-restore-verification.dump
    compose exec -T database psql --username practice_migrator --dbname practice_restore_verification \
      --tuples-only --no-align --command "SELECT count(*) FROM information_schema.tables WHERE table_schema IN ('reference','system','audit','import');"
    compose exec -T database dropdb --username practice_migrator practice_restore_verification
    compose exec -T database rm -f /tmp/practice-restore-verification.dump
    printf '%s\n' "Backup restore verification passed. The temporary verification database was removed."
    ;;
  *)
    printf '%s\n' "Usage: $0 {migrate|backup [path]|verify-backup <path>}" >&2
    exit 2
    ;;
esac
