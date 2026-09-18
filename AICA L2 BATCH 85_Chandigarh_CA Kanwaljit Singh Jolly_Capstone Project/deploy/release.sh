#!/usr/bin/env sh
# Promote a pre-pulled Task Checker image. The current release remains intact
# until the candidate passes its health check; failed promotion restores it.
set -eu

IMAGE="${1:?Usage: release.sh IMAGE}"
APP_DIR="${TASKCHECKER_APP_DIR:-/opt/apps/taskchecker}"
ENV_FILE="${TASKCHECKER_ENV_FILE:-$APP_DIR/.env}"
WEB_PORT="${TASKCHECKER_WEB_PORT:-8000}"
VALIDATION_ID="${TASKCHECKER_VALIDATION_WORKER_ID:-taskchecker-production-validation}"
LOGIN_ID="${TASKCHECKER_LOGIN_WORKER_ID:-taskchecker-production-login}"
VALIDATION_STOP_TIMEOUT="${TASKCHECKER_VALIDATION_STOP_TIMEOUT:-1800}"

WEB_CONTAINER="taskchecker-web"
VALIDATION_CONTAINER="taskchecker-worker"
LOGIN_CONTAINER="taskchecker-codex-login"
CANDIDATE_CONTAINER="taskchecker-web-candidate"
PROMOTING=0

test -f "$ENV_FILE" || {
    echo "Missing runtime environment file: $ENV_FILE" >&2
    exit 1
}

common_args() {
    printf '%s\n' \
        --env-file "$ENV_FILE" \
        --init \
        --security-opt no-new-privileges:true \
        --cap-drop ALL \
        --log-opt max-size=10m \
        --log-opt max-file=5 \
        --label com.taskchecker.managed=true \
        --label "com.taskchecker.image=$IMAGE"
}

validation_args() {
    common_args
    printf '%s\n' \
        --security-opt seccomp=unconfined \
        --security-opt apparmor=unconfined \
        --security-opt systempaths=unconfined
}

remove_candidate() {
    docker rm --force "$CANDIDATE_CONTAINER" >/dev/null 2>&1 || true
}

rollback() {
    echo "Promotion failed; restoring the previous Task Checker release." >&2
    set +e
    for container in "$WEB_CONTAINER" "$VALIDATION_CONTAINER" "$LOGIN_CONTAINER"; do
        docker rm --force "$container" >/dev/null 2>&1 || true
    done
    for container in "$WEB_CONTAINER" "$VALIDATION_CONTAINER" "$LOGIN_CONTAINER"; do
        if docker container inspect "${container}-rollback" >/dev/null 2>&1; then
            docker rename "${container}-rollback" "$container"
            docker start "$container" >/dev/null
        fi
    done
    remove_candidate
}

on_failure() {
    status=$?
    trap - EXIT HUP INT TERM
    if [ "$PROMOTING" -eq 1 ]; then
        rollback
    else
        remove_candidate
    fi
    exit "$status"
}
trap on_failure EXIT HUP INT TERM

echo "Running image import smoke check."
docker run --rm --env-file "$ENV_FILE" "$IMAGE" \
    python -c "import app_standalone, worker, codex_login_worker; print('Runtime imports passed')"

echo "Verifying the Codex Linux sandbox."
docker run --rm \
    $(validation_args) \
    "$IMAGE" \
    bwrap --ro-bind / / --proc /proc --dev /dev --unshare-all --die-with-parent -- /bin/true

echo "Starting isolated web candidate."
remove_candidate
# A random loopback port avoids collisions and does not expose the candidate publicly.
docker run --detach --name "$CANDIDATE_CONTAINER" \
    $(common_args) \
    --restart no \
    --publish 127.0.0.1::8000 \
    "$IMAGE" >/dev/null
CANDIDATE_PORT=$(docker port "$CANDIDATE_CONTAINER" 8000/tcp | sed 's/.*://')

candidate_ready=0
attempt=1
while [ "$attempt" -le 30 ]; do
    if curl --fail --silent --show-error "http://127.0.0.1:$CANDIDATE_PORT/health" >/dev/null; then
        candidate_ready=1
        break
    fi
    if [ "$(docker inspect --format '{{.State.Running}}' "$CANDIDATE_CONTAINER")" != "true" ]; then
        break
    fi
    sleep 2
    attempt=$((attempt + 1))
done
if [ "$candidate_ready" -ne 1 ]; then
    docker logs "$CANDIDATE_CONTAINER" || true
    echo "Candidate health check failed; the current release was not changed." >&2
    false
fi
remove_candidate

OLD_IMAGE=$(docker inspect --format '{{.Config.Image}}' "$WEB_CONTAINER" 2>/dev/null || true)
PROMOTING=1
PROMOTION_STARTED=$(date -u '+%Y-%m-%dT%H:%M:%S.%6NZ')

echo "Preserving the current containers for automatic rollback."
for container in "$WEB_CONTAINER" "$VALIDATION_CONTAINER" "$LOGIN_CONTAINER"; do
    docker rm --force "${container}-rollback" >/dev/null 2>&1 || true
    if docker container inspect "$container" >/dev/null 2>&1; then
        if [ "$container" = "$VALIDATION_CONTAINER" ]; then
            echo "Draining any in-flight validation (timeout: ${VALIDATION_STOP_TIMEOUT}s)."
            docker stop --time "$VALIDATION_STOP_TIMEOUT" "$container" >/dev/null
        else
            docker stop --time 30 "$container" >/dev/null
        fi
        docker rename "$container" "${container}-rollback"
    fi
done

echo "Creating the new release containers."
docker create --name "$WEB_CONTAINER" \
    $(common_args) \
    --restart unless-stopped \
    --publish "127.0.0.1:$WEB_PORT:8000" \
    "$IMAGE" >/dev/null

docker create --name "$VALIDATION_CONTAINER" \
    $(validation_args) \
    --restart unless-stopped \
    --stop-timeout "$VALIDATION_STOP_TIMEOUT" \
    --env "TASKCHECKER_WORKER_ID=$VALIDATION_ID" \
    "$IMAGE" python -u worker.py >/dev/null

docker create --name "$LOGIN_CONTAINER" \
    $(common_args) \
    --restart unless-stopped \
    --env "TASKCHECKER_LOGIN_WORKER_ID=$LOGIN_ID" \
    "$IMAGE" python -u codex_login_worker.py >/dev/null

docker start "$WEB_CONTAINER" "$VALIDATION_CONTAINER" "$LOGIN_CONTAINER" >/dev/null

echo "Verifying the promoted web process."
web_ready=0
attempt=1
while [ "$attempt" -le 30 ]; do
    if curl --fail --silent --show-error "http://127.0.0.1:$WEB_PORT/health" >/dev/null; then
        web_ready=1
        break
    fi
    sleep 2
    attempt=$((attempt + 1))
done
test "$web_ready" -eq 1

echo "Verifying fresh validation and login worker heartbeats."
workers_ready=0
attempt=1
while [ "$attempt" -le 30 ]; do
    if docker exec "$WEB_CONTAINER" python -m deploy.verify_workers \
        --max-age 30 --after "$PROMOTION_STARTED" "$VALIDATION_ID" "$LOGIN_ID"; then
        workers_ready=1
        break
    fi
    sleep 2
    attempt=$((attempt + 1))
done
if [ "$workers_ready" -ne 1 ]; then
    docker logs --tail 100 "$VALIDATION_CONTAINER" || true
    docker logs --tail 100 "$LOGIN_CONTAINER" || true
    false
fi

PROMOTING=0
trap - EXIT HUP INT TERM

for container in "$WEB_CONTAINER" "$VALIDATION_CONTAINER" "$LOGIN_CONTAINER"; do
    docker rm --force "${container}-rollback" >/dev/null 2>&1 || true
done

mkdir -p "$APP_DIR"
printf '%s\n' "$IMAGE" > "$APP_DIR/current-image"
if [ -n "$OLD_IMAGE" ]; then
    printf '%s\n' "$OLD_IMAGE" > "$APP_DIR/previous-image"
fi

echo "Task Checker release is healthy: $IMAGE"
