#!/usr/bin/env sh
set -eu

action="${1:-start}"
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repository_root=$(CDPATH= cd -- "$script_dir/../.." && pwd)

cd "$repository_root"

ensure_environment() {
  if [ ! -f .env ]; then
    cp .env.example .env
    printf '%s\n' "Created .env from .env.example. Change its password before non-local use."
  fi
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf '%s\n' "Required command is not installed: $1" >&2
    exit 1
  fi
}

case "$action" in
  bootstrap)
    ensure_environment
    require_command pnpm
    (cd web && pnpm install --frozen-lockfile)
    ;;
  start)
    ensure_environment
    require_command docker
    docker compose --env-file .env -f deploy/compose/compose.yml up --build --detach
    ;;
  stop)
    ensure_environment
    require_command docker
    docker compose --env-file .env -f deploy/compose/compose.yml down
    ;;
  verify)
    require_command dotnet
    require_command pnpm
    dotnet restore PracticeManagement.slnx
    dotnet build PracticeManagement.slnx --configuration Release --no-restore
    dotnet run --project tests/Practice.Architecture.Tests/Practice.Architecture.Tests.csproj --configuration Release --no-build
    dotnet run --project tests/Practice.Database.Tests/Practice.Database.Tests.csproj --configuration Release --no-build
    dotnet run --project tests/Practice.Identity.Tests/Practice.Identity.Tests.csproj --configuration Release --no-build
    dotnet run --project tests/Practice.Scheduling.Tests/Practice.Scheduling.Tests.csproj --configuration Release --no-build
    dotnet run --project tests/Practice.Billing.Tests/Practice.Billing.Tests.csproj --configuration Release --no-build
    dotnet run --project tests/Practice.Reporting.Tests/Practice.Reporting.Tests.csproj --configuration Release --no-build
    dotnet run --project tests/Practice.WorkbookProfiler.Tests/Practice.WorkbookProfiler.Tests.csproj --configuration Release --no-build
    # The API integration suite needs a disposable PostgreSQL instance. It is started here and
    # always removed, and it never touches the development compose volume.
    if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
      integration_container="practice-verify-db-$$"
      integration_password=$(head -c 18 /dev/urandom | od -An -tx1 | tr -d ' \n')
      trap 'docker rm -f "$integration_container" >/dev/null 2>&1 || true' EXIT INT TERM
      docker run -d --name "$integration_container" -p 127.0.0.1:55432:5432 \
        -e POSTGRES_DB=practice_verify -e POSTGRES_USER=practice_verify \
        -e POSTGRES_PASSWORD="$integration_password" \
        --tmpfs /var/lib/postgresql postgres:18-alpine >/dev/null
      integration_ready=0
      for _ in $(seq 1 40); do
        if docker exec "$integration_container" pg_isready -U practice_verify -d practice_verify >/dev/null 2>&1; then
          integration_ready=1
          break
        fi
        sleep 2
      done
      if [ "$integration_ready" = "1" ]; then
        PRACTICE_TEST_DATABASE="Host=127.0.0.1;Port=55432;Database=practice_verify;Username=practice_verify;Password=$integration_password" \
          dotnet run --project tests/Practice.Api.IntegrationTests/Practice.Api.IntegrationTests.csproj --configuration Release --no-build
      else
        printf '%s\n' "Disposable PostgreSQL did not become ready; API integration checks were skipped." >&2
      fi
      docker rm -f "$integration_container" >/dev/null 2>&1 || true
      trap - EXIT INT TERM
    else
      printf '%s\n' "Docker is unavailable; API integration checks were skipped." >&2
    fi
    (cd web && pnpm install --frozen-lockfile && pnpm lint && pnpm test && pnpm build)
    ;;
  *)
    printf '%s\n' "Usage: $0 {bootstrap|start|stop|verify}" >&2
    exit 2
    ;;
esac
