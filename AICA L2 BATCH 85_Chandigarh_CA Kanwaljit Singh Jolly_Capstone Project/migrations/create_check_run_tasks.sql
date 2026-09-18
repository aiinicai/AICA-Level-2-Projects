CREATE TABLE IF NOT EXISTS check_run_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    check_run_id UUID NOT NULL REFERENCES check_runs(id) ON DELETE CASCADE,
    stage TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    attempt_count INT NOT NULL DEFAULT 0,
    payload JSONB,
    result JSONB,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS check_run_tasks_status_idx ON check_run_tasks(status);
CREATE INDEX IF NOT EXISTS check_run_tasks_check_run_idx ON check_run_tasks(check_run_id);
