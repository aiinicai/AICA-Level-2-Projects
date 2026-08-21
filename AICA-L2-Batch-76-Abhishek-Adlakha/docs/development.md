# Development Guide

## Working rules

1. Read the architecture blueprint, ADR index, glossary and the relevant module documentation.
2. State scope and expected files before editing.
3. Identify database, API, UI, permission, audit and test impact.
4. Change only the authorized phase or feature.
5. Keep business rules out of endpoints and React components.
6. Use migrations for every schema change; do not manually edit production databases.
7. Run `make verify` and report results and limitations.

## Repository layout

- `src/Practice.Api`: HTTP composition root and cross-cutting middleware.
- `src/Practice.Worker`: background host; no jobs are registered in Phase 0.
- `src/Practice.BuildingBlocks`: small stable primitives only.
- `src/Modules`: created module-by-module in later authorized phases.
- `web`: React application with feature folders added only as phases require.
- `tests`: automated boundary and behavior checks.
- `deploy`: container/reverse-proxy/release assets.
- `docs`: architecture, decisions, domain and operations documentation.

## Commands

Windows PowerShell:

```powershell
.\deploy\scripts\practice.ps1 bootstrap
.\deploy\scripts\practice.ps1 verify
.\deploy\scripts\practice.ps1 start
.\deploy\scripts\practice.ps1 stop
```

macOS/Linux:

```bash
./deploy/scripts/practice.sh bootstrap
./deploy/scripts/practice.sh verify
./deploy/scripts/practice.sh start
./deploy/scripts/practice.sh stop
```

Make targets are macOS/Linux aliases. Both operating-system scripts invoke the same Compose file and retain the PostgreSQL volume when stopping. Data removal requires a separate explicit destructive operation and is not part of routine development.

After the Phase 2 migration, the first administrator is created exactly once from a local terminal:

```bash
docker compose --env-file .env -f deploy/compose/compose.yml --profile admin run --rm admin \
  bootstrap-admin --mobile YOUR_10_DIGIT_MOBILE --name "Abhishek Adlakha"
```

The password is read without echo. Never provide it in chat or add it to `.env`/source control. Use the equivalent command from PowerShell on Windows. Production uses the native Windows Server package and its separate runbook, not this development Compose stack.

For local password recovery, run the same administrator utility with `reset-password --mobile YOUR_10_DIGIT_MOBILE`. It asks for the new password twice, clears lockout state, revokes existing sessions and writes an audit event without logging the password.

## Definition of done

- Scope and acceptance criteria met.
- Tests cover the rule and denial/failure paths.
- Compiler/type/lint/build checks pass.
- Schema change includes a reviewed migration and forward-migration test.
- Permissions and audit behavior are explicit.
- API/OpenAPI and operational/domain documentation are updated where affected.
- Files, migrations, tests, manual verification, limitations and risks are reported.
