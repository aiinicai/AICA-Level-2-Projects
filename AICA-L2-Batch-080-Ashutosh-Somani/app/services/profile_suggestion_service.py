import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from app.models.correction import CorrectionEvent

logger = logging.getLogger(__name__)

class ProfileSuggestionService:
    def __init__(self, config):
        self.config = config
        if hasattr(config, 'get') and hasattr(config, 'read'):
            temp_dir_str = config.get('paths', 'temp', fallback='temp')
        elif hasattr(config, 'get') and 'APP_CONFIG' in config:
            temp_dir_str = config['APP_CONFIG'].get('paths', 'temp', fallback='temp')
        else:
            temp_dir_str = 'temp'
        self.temp_dir = Path(temp_dir_str)

    def get_suggestions_path(self, job_id: str) -> Path:
        return self.temp_dir / 'jobs' / job_id / 'review' / 'profile_suggestions.json'

    def generate_suggestion(self, job_id: str, event: CorrectionEvent):
        """
        Deterministically suggests profile reviews without mutating profiles.
        """
        # We only generate suggestions if a profile was actually used.
        # Check if job used a profile.
        from app.database.db import get_db_connection
        profile_id = None
        with get_db_connection(self.config) as conn:
            row = conn.execute("SELECT profile_id FROM processing_jobs WHERE id = ?", (job_id,)).fetchone()
            if row and row[0]:
                profile_id = row[0]
                
        if not profile_id:
            return
            
        suggestion = None
        if event.action.value == "ROW_MERGE":
            suggestion = {
                "type": "REVIEW_CONTINUATION_RULE",
                "reason": "User manually merged adjacent rows, indicating possible multiline continuation rule mismatch.",
                "profile_id": profile_id
            }
        elif event.action.value == "MARK_NON_TRANSACTION":
            suggestion = {
                "type": "REVIEW_FOOTER_RULE",
                "reason": "User excluded a row, indicating a potential repeated header or footer false-positive.",
                "profile_id": profile_id
            }
        
        if suggestion:
            event.profile_suggestion_created = True
            
            path = self.get_suggestions_path(job_id)
            suggestions = []
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    suggestions = json.load(f)
            
            # Avoid duplicates of same type
            if not any(s["type"] == suggestion["type"] for s in suggestions):
                suggestions.append(suggestion)
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(suggestions, f, indent=2)

    def get_suggestions(self, job_id: str) -> List[Dict[str, Any]]:
        path = self.get_suggestions_path(job_id)
        if not path.exists():
            return []
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
