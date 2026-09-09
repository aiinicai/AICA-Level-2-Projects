# Task Checker Codex runtime

Task Checker now uses the official Python Codex SDK as its production validation engine. The web process never executes a check itself: it authenticates the user, verifies tenant permissions, snapshots the superadmin-owned agent configuration, and appends a durable queue item. `worker.py` claims jobs atomically and runs one ephemeral Codex thread with one structured-output turn.

## Roles and account ownership

- Each tenant has exactly one active `super_admin`.
- The superadmin connects one tenant OneDrive account and one tenant ChatGPT account, creates complete agent configurations, and assigns agents to admins.
- Admins see only assigned agents. Running an agent sends an empty request body; they cannot override workflow text, files, model, effort, or integration accounts.
- Admins see only runs they requested. The superadmin sees every tenant run.
- Codex `PASS` is final automatically. `FAIL` and `INDETERMINATE` are provisional and create a superadmin review item.

## First-time setup

1. Use Python 3.10 or newer and create a clean virtual environment.
2. Install `requirements.txt`.
3. Apply [`migrations/20260821_tenant_codex_runtime.sql`](../migrations/20260821_tenant_codex_runtime.sql) in the Supabase SQL editor.
4. Copy `.env.example` to `.env`, configure Supabase and Microsoft OAuth, and generate `TASKCHECKER_CREDENTIAL_KEY` as shown in that file.
5. Start all three processes:

   ```powershell
   python app_standalone.py
   python worker.py
   python codex_login_worker.py
   ```

6. Sign in as the tenant superadmin. In Settings, connect the tenant OneDrive account, then open ChatGPT / Codex and complete the device-code login.
7. Create an agent, select the task folder, choose its input/output files in step 3 and its Workflow subfolder/files in step 4, then choose the Codex model, effort, context/reference files, and assigned admins. The text box is only for optional additional instructions.

The Flask UI is at `http://localhost:5000`. An admin only opens an assigned agent and presses **Run Check**.

## Execution lifecycle

`QUEUED → PREPARING → RUNNING → FINALIZING → COMPLETED`

The SQL claim function provides FIFO ordering while skipping a tenant that already has an active run. This enforces one active Codex run per tenant. Expired leases can be reclaimed, transient errors are retried with backoff, and exhausted jobs finish as `ERROR`.

During a run, the worker:

1. Downloads the immutable configuration snapshot from the tenant's OneDrive into an ephemeral directory.
2. Decrypts the tenant's Codex `auth.json` into a different temporary directory that is outside the agent workspace.
3. Starts the SDK with `ApprovalMode.deny_all`, `Sandbox.workspace_write`, live web search, network access, an ephemeral thread, and a JSON output schema.
4. Persists the verdict, cited evidence, warnings, model, effort, SDK version, thread/turn identifiers, and token usage.
5. Deletes both temporary directories.

The SDK uses the ChatGPT account's Codex entitlement and limits because the superadmin completed ChatGPT device login. It does not use `OPENAI_API_KEY` in the primary path.

## Operations

- `TASKCHECKER_VALIDATOR=codex` is the default and production setting.
- `TASKCHECKER_VALIDATOR=legacy` is the explicit rollback switch. The app never falls back automatically when Codex fails.
- Monitor `/health`, `worker_heartbeats`, queued task age, retries, and `check_runs.run_status`.
- Back up `TASKCHECKER_CREDENTIAL_KEY` in a secret manager. Losing it makes stored tenant Codex credentials unrecoverable. Rotating it requires decrypting/re-encrypting every credential or reconnecting each tenant.
- Run one validation worker process initially. Tenant serialization is also enforced in the database, so additional workers may be added later without allowing two simultaneous runs for one tenant.

## Production deployment to the Contabo VPS

Production uses the same GHCR-to-SSH shape as Assure, but deploys Task Checker's
three processes from one immutable image. A push to `main` runs the tests, builds
the image, pushes both the commit-SHA and `latest` tags, and connects to the VPS.

The VPS deployment then:

1. Runs an import smoke test using the real production environment.
2. Starts the new web image on a random loopback port and waits for `/health`.
3. Gracefully drains an in-flight validation, then preserves the current three
   containers as rollback containers.
4. Starts `taskchecker-web`, `taskchecker-worker`, and
   `taskchecker-codex-login` from the exact same image.
5. Waits for the public web port and fresh Supabase heartbeats from both workers.
6. Restores the old containers automatically if promotion fails. On success it
   retains the old image and records it in `/opt/apps/taskchecker/previous-image`.

This avoids replacing a working release with an image that cannot boot. The final
port swap has a short interruption while the old web container releases port 8000.

### One-time VPS setup

The SSH deployment user must be able to run Docker without `sudo`. Docker, nginx,
and curl must be installed. Create the application directory and its environment:

```bash
sudo install -d -m 750 -o "$USER" -g "$USER" /opt/apps/taskchecker
sudo install -m 600 /path/to/completed-taskchecker.env /opt/apps/taskchecker/.env
```

At minimum, the environment needs the production Flask secret, Supabase URL and
keys, `TASKCHECKER_CREDENTIAL_KEY`, Microsoft OAuth values, `APP_URL`, and
`TASKCHECKER_VALIDATOR=codex`. Use `FRONTEND_URL` and `APP_URL` with the public
HTTPS origin. Do not put tenant ChatGPT credentials in this file; those are
connected in the app and encrypted in Supabase.

If the earlier systemd deployment is running, disable it before the first Docker
release so it does not hold port 8000:

```bash
sudo systemctl disable --now taskchecker-web taskchecker-worker taskchecker-codex-login
```

Install `deploy/nginx-taskchecker.conf` as the nginx site, adjust the hostname if
needed, enable it, and add TLS (for example with Certbot):

```bash
sudo cp deploy/nginx-taskchecker.conf /etc/nginx/sites-available/taskchecker
sudo ln -s /etc/nginx/sites-available/taskchecker /etc/nginx/sites-enabled/taskchecker
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d verify.infinitysolutons.app
```

### GitHub configuration

Create a protected GitHub environment named `production`, then configure these
repository or environment secrets:

- `VPS_HOST`: Contabo server hostname or IP.
- `VPS_USER`: non-root deployment user in the Docker group.
- `VPS_PORT`: SSH port, normally `22`.
- `VPS_SSH_KEY`: private SSH key for that user.
- `GHCR_TOKEN`: GitHub classic PAT with `read:packages` for pulling a private image.

The workflow uses GitHub's built-in token to push the image. It never sends the
Supabase, Microsoft, Flask, or credential-encryption secrets through GitHub; those
remain only in `/opt/apps/taskchecker/.env` on the VPS.

Merge the deployment files into `main` to enable automatic production deployment.
The workflow can also be run manually with a branch, tag, or commit through
**Actions → Deploy to VPS → Run workflow**.

### Operations and rollback

```bash
docker ps --filter label=com.taskchecker.managed=true
docker logs --tail 100 taskchecker-web
docker logs --tail 100 taskchecker-worker
docker logs --tail 100 taskchecker-codex-login
curl --fail http://127.0.0.1:8000/health
cat /opt/apps/taskchecker/current-image
cat /opt/apps/taskchecker/previous-image
```

Re-running the workflow with an earlier commit deploys that immutable image through
the same safety checks. Images are deliberately not pruned by the workflow, so the
previous release remains locally available for recovery.

The `taskchecker-*.service` files remain available as a non-containerized fallback,
but they are not used by the GitHub deployment.
