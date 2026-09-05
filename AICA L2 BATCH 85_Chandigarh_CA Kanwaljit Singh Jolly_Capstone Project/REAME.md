# Task Checker

Task Checker is an AI-powered workflow validation system. It checks completed task outputs against their source files and workflow instructions, records evidence for each verdict, and routes uncertain or failed results to a human-review queue.

The application supports two ways to run checks:

- A multi-tenant web application that uses Supabase, OneDrive, and the official Codex SDK.
- A command-line runner for checking a local task folder without the web interface or OneDrive.

## Main features

- Create reusable checking agents with predefined workflow, input, output, and reference files.
- Connect a tenant-owned Microsoft OneDrive account for task files.
- Connect a tenant-owned ChatGPT account for Codex validation.
- Queue checks and process them in a background worker.
- Produce `PASS`, `FAIL`, or `INDETERMINATE` verdicts with cited evidence.
- Automatically accept a `PASS` result and send other verdicts to human review.
- Track run progress, retries, model details, token usage, and downloadable PDF reports.
- Support role-based access for superadmins and assigned admins.
- Run deterministic and AI-assisted validation against local files.

## How it works

```text
Browser UI
    |
    v
Flask API  -----> Supabase (users, agents, queues, runs, reviews)
    |                         |
    |                         v
    |                 Validation worker
    |                         |
    v                         v
OneDrive files <------> Temporary workspace <------> Codex SDK
```

For the production workflow, the Flask application validates the request and adds a durable queue item. `worker.py` claims the job, downloads the configured files into a temporary workspace, runs Codex, stores the result in Supabase, and removes the temporary files. `codex_login_worker.py` separately handles ChatGPT device-code login.

## Technology stack

- **Backend:** Python 3.10+, Flask, Gunicorn
- **Frontend:** HTML, CSS, and vanilla JavaScript
- **Database and authentication:** Supabase
- **File storage:** Microsoft OneDrive through Microsoft Graph
- **AI validation:** OpenAI Codex SDK, with a legacy OpenAI/OpenRouter validation pipeline available
- **Document processing:** pandas, openpyxl, python-docx, and PyMuPDF
- **Testing and linting:** pytest and Ruff
- **Deployment:** Docker, nginx, systemd fallback services, and GHCR-based releases

## Project structure

```text
.
|-- api/                     Flask API blueprints
|-- services/                Validation, file, AI, reporting, and integration logic
|-- models/                  Validation and rule data models
|-- static/                  Browser JavaScript and CSS
|-- migrations/              Supabase database migrations
|-- tests/                   Unit and offline integration tests
|-- docs/CODEX_RUNTIME.md    Detailed Codex runtime and deployment guide
|-- deploy/                  nginx, systemd, release, and worker utilities
|-- app_standalone.py        Flask application entry point
|-- worker.py                Queued Codex validation worker
|-- codex_login_worker.py    ChatGPT device-login worker
|-- run_local.py             Local-folder command-line checker
|-- wsgi.py                  WSGI entry point
|-- Dockerfile               Production container image
`-- requirements.txt         Python dependencies
```

## Prerequisites

- Python 3.10 or newer
- A Supabase project
- A Microsoft Entra application with Microsoft Graph/OneDrive access
- A ChatGPT account with Codex access for the primary validation path
- Docker, if running the containerized deployment

## Local installation

1. Clone the repository and enter the project directory.

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   On Windows PowerShell:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install the dependencies:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root. At minimum, the web application needs:

   ```dotenv
   FLASK_SECRET_KEY=replace-with-a-long-random-secret

   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-anon-key
   SUPABASE_SERVICE_KEY=your-service-role-key

   CLIENT_ID=your-microsoft-application-client-id
   CLIENT_SECRET=your-microsoft-application-client-secret
   TENANT_ID=your-microsoft-tenant-id
   ONEDRIVE_REDIRECT_URI=http://localhost:5000/onedrive/callback

   TASKCHECKER_CREDENTIAL_KEY=your-fernet-key
   TASKCHECKER_VALIDATOR=codex

   APP_URL=http://localhost:5000
   FRONTEND_URL=http://localhost:5000
   ```

   Generate the credential-encryption key with:

   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

   Keep `.env`, the Supabase service-role key, Microsoft client secret, and credential-encryption key out of version control.

5. Apply the required SQL migrations from `migrations/` to the Supabase project. For the current tenant-scoped Codex runtime, start with `migrations/20260821_tenant_codex_runtime.sql` and apply any later migrations needed by the checked-out version.

## Running the web application

The complete application uses three processes. Open a separate terminal for each command, activate the same virtual environment, and load the same `.env` configuration.

```bash
python app_standalone.py
python worker.py
python codex_login_worker.py
```

Then open <http://localhost:5000>.

Useful endpoints include:

- `GET /health` — service health check
- `GET /api` — basic API information
- `GET|POST /api/agents` — list or create checking agents
- `POST /api/agents/<agent_id>/run-check` — queue a check
- `GET /api/check-runs` — list visible runs
- `GET /api/check-runs/<run_id>` — retrieve run details
- `GET /api/check-runs/<run_id>/report.pdf` — download a report
- `GET /api/human-review/queue` — view pending reviews

On first use, sign in as the tenant superadmin, connect OneDrive, complete the ChatGPT/Codex device login, create an agent, select its files and workflow, and assign it to the appropriate admins.

## Running a local-folder check

The command-line runner does not need OneDrive or the browser UI. Prepare a folder in this format:

```text
task-folder/
|-- Inputs/
|   `-- source files
|-- Outputs/
|   `-- completed files to validate
`-- Workflow.txt
```

For this legacy/local pipeline, configure either `OPENAI_API_KEY` or `OPENROUTER_API_KEY` in `.env`, then run:

```bash
python run_local.py "/path/to/task-folder"
```

Optional arguments:

```bash
python run_local.py "/path/to/task-folder" \
  --desc "Reconcile output records against the source data" \
  --brief

python run_local.py "/path/to/task-folder" --json
```

The model can be selected with `AI_VALIDATION_MODEL`, `AI_TOOL_LOOP_MODEL`, or `AI_PRIMARY_MODEL`.

## Tests and code quality

The test suite uses stubbed AI responses for offline, deterministic validation.

```bash
python -m pytest
python -m ruff check .
```

## Docker

Build the image:

```bash
docker build -t task-checker .
```

Run the web process with an environment file:

```bash
docker run --rm --env-file .env -p 8000:8000 task-checker
```

The image's default command starts Gunicorn on port `8000`. Production also requires worker and login-worker containers created from the same image with their commands changed to `python worker.py` and `python codex_login_worker.py`.

## Validation lifecycle

```text
QUEUED -> PREPARING -> RUNNING -> FINALIZING -> COMPLETED
```

Each tenant is limited to one active validation at a time. Transient failures are retried with exponential backoff; exhausted jobs end in `ERROR`. A Codex `PASS` becomes the final verdict automatically, while `FAIL` and `INDETERMINATE` require superadmin review.

## Security notes

- The application refuses to start without `FLASK_SECRET_KEY`.
- Tenant Codex credentials are encrypted before being stored in Supabase.
- Codex validation runs in an ephemeral workspace with denied approval prompts and workspace-only write access.
- Temporary workspaces and decrypted authentication files are deleted after each run.
- The Supabase service-role key must only be available to trusted backend processes.
- Losing `TASKCHECKER_CREDENTIAL_KEY` makes stored tenant Codex credentials unrecoverable.

## Further documentation

See [docs/CODEX_RUNTIME.md](docs/CODEX_RUNTIME.md) for the detailed account model, worker lifecycle, production deployment, monitoring, and rollback procedure.

