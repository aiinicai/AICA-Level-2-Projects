-- Week 4: Multi-Model Consensus & Human Review Queue
-- Database schema for consensus decision-making and conflict resolution

-- Table: model_consensus_results
-- Stores results from multi-model consensus checks
CREATE TABLE IF NOT EXISTS model_consensus_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    check_run_id UUID REFERENCES check_runs(id) ON DELETE CASCADE,
    gpt4_response JSONB,
    claude_response JSONB,
    gemini_response JSONB,
    agreement_level FLOAT NOT NULL CHECK (agreement_level >= 0 AND agreement_level <= 1),
    consensus_verdict JSONB NOT NULL,
    conflicts_detected JSONB,
    escalated_to_human BOOLEAN DEFAULT FALSE,
    human_review_id UUID,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_consensus_check_run ON model_consensus_results(check_run_id);
CREATE INDEX idx_consensus_escalated ON model_consensus_results(escalated_to_human);
CREATE INDEX idx_consensus_created ON model_consensus_results(created_at);

-- Table: human_reviews
-- Human review queue for conflict resolution
CREATE TABLE IF NOT EXISTS human_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    check_run_id UUID REFERENCES check_runs(id) ON DELETE CASCADE,
    conflicts JSONB NOT NULL,
    model_responses JSONB NOT NULL,
    consensus_metadata JSONB,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'resolved', 'cancelled')),
    assigned_to UUID REFERENCES profiles(id),
    resolved_by UUID REFERENCES profiles(id),
    resolution JSONB,
    resolution_reasoning TEXT,
    feedback_to_ai TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);

CREATE INDEX idx_review_status ON human_reviews(status);
CREATE INDEX idx_review_assigned ON human_reviews(assigned_to);
CREATE INDEX idx_review_check_run ON human_reviews(check_run_id);
CREATE INDEX idx_review_created ON human_reviews(created_at);

-- Table: human_resolution_feedback
-- Stores feedback from human resolutions for AI learning
CREATE TABLE IF NOT EXISTS human_resolution_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id UUID REFERENCES human_reviews(id) ON DELETE CASCADE,
    correct_model TEXT CHECK (correct_model IN ('gpt-4', 'claude', 'gemini')),
    correction_type TEXT NOT NULL,
    learning_notes TEXT,
    applied_to_future_checks BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_feedback_review ON human_resolution_feedback(review_id);
CREATE INDEX idx_feedback_model ON human_resolution_feedback(correct_model);
CREATE INDEX idx_feedback_created ON human_resolution_feedback(created_at);

-- Add foreign key relationship for human_review_id in model_consensus_results
ALTER TABLE model_consensus_results
ADD CONSTRAINT fk_consensus_human_review
FOREIGN KEY (human_review_id) REFERENCES human_reviews(id) ON DELETE SET NULL;

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_human_reviews_updated_at
    BEFORE UPDATE ON human_reviews
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- View: pending_reviews_summary
-- Quick view of pending reviews with check run details
CREATE OR REPLACE VIEW pending_reviews_summary AS
SELECT
    hr.id AS review_id,
    hr.check_run_id,
    hr.status,
    hr.assigned_to,
    hr.created_at,
    cr.agent_id,
    a.user_id,
    cr.status AS check_status,
    (hr.conflicts::jsonb->0->>'severity')::FLOAT AS max_conflict_severity,
    jsonb_array_length(hr.conflicts) AS conflict_count
FROM human_reviews hr
JOIN check_runs cr ON hr.check_run_id = cr.id
JOIN agents a ON cr.agent_id = a.id
WHERE hr.status IN ('pending', 'in_progress')
ORDER BY
    hr.created_at ASC;

-- View: consensus_metrics
-- Metrics for multi-model consensus performance
CREATE OR REPLACE VIEW consensus_metrics AS
SELECT
    DATE(created_at) AS date,
    COUNT(*) AS total_consensus_checks,
    AVG(agreement_level) AS avg_agreement_level,
    COUNT(*) FILTER (WHERE agreement_level >= 0.67) AS consensus_reached,
    COUNT(*) FILTER (WHERE agreement_level < 0.67) AS consensus_failed,
    COUNT(*) FILTER (WHERE escalated_to_human = TRUE) AS escalated_count
FROM model_consensus_results
GROUP BY DATE(created_at)
ORDER BY date DESC;

COMMENT ON TABLE model_consensus_results IS 'Week 4: Multi-model consensus results (GPT-4, Claude, Gemini)';
COMMENT ON TABLE human_reviews IS 'Week 4: Human review queue for conflict resolution';
COMMENT ON TABLE human_resolution_feedback IS 'Week 4: Learning feedback from human resolutions';
