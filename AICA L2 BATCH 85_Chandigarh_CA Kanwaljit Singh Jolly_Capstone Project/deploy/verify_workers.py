"""Fail unless the expected production workers have fresh Supabase heartbeats."""

import argparse
from datetime import datetime, timezone

from supabase_config import supabase_admin


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("worker_ids", nargs="+")
    parser.add_argument("--max-age", type=float, default=30.0)
    parser.add_argument(
        "--after",
        type=_timestamp,
        help="require a heartbeat at or after this ISO-8601 deployment timestamp",
    )
    args = parser.parse_args()

    response = (
        supabase_admin.table("worker_heartbeats")
        .select("worker_id,worker_type,last_seen_at")
        .in_("worker_id", args.worker_ids)
        .execute()
    )
    rows = {row["worker_id"]: row for row in (response.data or [])}
    now = datetime.now(timezone.utc)
    problems = []
    for worker_id in args.worker_ids:
        row = rows.get(worker_id)
        if not row:
            problems.append(f"{worker_id}: missing")
            continue
        age = (now - _timestamp(row["last_seen_at"])).total_seconds()
        if age > args.max_age:
            problems.append(f"{worker_id}: stale ({age:.1f}s)")
        elif args.after and _timestamp(row["last_seen_at"]) < args.after:
            problems.append(f"{worker_id}: has not heartbeated during this release")

    if problems:
        print("Worker heartbeat check failed: " + "; ".join(problems))
        return 1

    print("Fresh worker heartbeats: " + ", ".join(args.worker_ids))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
