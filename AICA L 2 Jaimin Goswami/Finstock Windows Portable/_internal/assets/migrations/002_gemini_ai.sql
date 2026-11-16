-- Migration 002: Gemini AI Analysis Cache
CREATE TABLE IF NOT EXISTS event_ai_cache (
    event_id TEXT PRIMARY KEY,
    analysis_text TEXT NOT NULL,
    model TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_event_ai_cache_created ON event_ai_cache(created_at);
