# BRMCo Accounting Hub — Server Host

Central services for BRMCo Accounting Hub. It runs on the BRMCo server or cloud, never on a client PC.

**Phase 1 scope (deliberately small):** a clean FastAPI service that fixes the API contract with Local Hosts (`GET /health`, `GET /version`). It also reserves placeholder modules for auth, AI, users, clients and central settings. It holds **no accounting logic** and **never talks to TallyPrime**, because Tally stays on the client's computer.

## Setup

```bash
cd brmco-accounting-server
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # optional; Linux/macOS: cp
```

## Run

Development:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

Open http://127.0.0.1:8001/docs for interactive API docs. These are disabled when `ENVIRONMENT=production`.

Production (Linux example): run uvicorn behind a reverse proxy (Nginx or Caddy) that terminates **HTTPS** for your domain, for example `https://api.brmco.in`:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 2 --proxy-headers
```

## Test

```bash
pytest -q
```

## API (Phase 1)

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness. `{"status":"ok","application":"BRMCo Accounting Hub Server","version":"1.0.0","time":"…","components":{…}}` |
| GET | `/version` | Compatibility. Adds `api_version`, `min_local_version`, `environment`, `features` |
| GET | `/api/v1/auth` | Placeholder: `{"module":"auth","enabled":false,"planned_phase":5,…}` |
| GET | `/api/v1/ai` | Placeholder (Phase 4) |
| GET | `/api/v1/users` | Placeholder (Phase 5) |
| GET | `/api/v1/clients` | Placeholder (Phase 5) |
| GET | `/api/v1/settings` | Placeholder (Phase 5) |

`/health` and `/version` are unversioned and permanent. Everything else lives under `/api/v1/…`. A breaking change goes to `/api/v2/…` so that older Local Hosts keep working.

## Structure

```
app/
  main.py               app factory, routers, error handler
  config/settings.py    environment settings (secrets as SecretStr)
  config/logging_config.py  logging with secret redaction
  api/                  health, version (+ placeholders: auth, ai, users, clients, settings)
  services/             auth_service, ai_service, client_service (stubs)
  repositories/         base.py (interface), memory.py (Phase 1), factory.py (backend switch)
tests/test_server.py
```

## Adding MongoDB later (Phase 5)

1. `pip install pymongo` and add it to `requirements.txt`.
2. Implement `MongoRepository(DocumentRepository)` in `app/repositories/mongo.py`.
3. Return it from `build_repositories()` when `REPOSITORY_BACKEND=mongodb`.
4. Set `MONGODB_URI` in the server `.env`.

Services depend only on the `DocumentRepository` interface, so nothing else changes.

## Security rules

- Secrets (`SECRET_KEY`, `AI_API_KEY`, `MONGODB_URI`) exist **only** in this server's environment. They are never returned by any endpoint and never copied to a Local Host.
- Log output passes through a redaction filter.
- Local Host → Server Host traffic must use HTTPS in production.
- AI providers are called **only** from this server (Phase 4). The Local Host never calls them directly.
