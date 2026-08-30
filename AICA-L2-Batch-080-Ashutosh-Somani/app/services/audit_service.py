import json
import os
import uuid
import datetime
import logging
from typing import List, Optional
from pathlib import Path

from app.models.correction import CorrectionEvent

logger = logging.getLogger(__name__)

class AuditService:
    def __init__(self, config):
        self.config = config
        
        if hasattr(config, 'get') and hasattr(config, 'read'):
            temp_dir_str = config.get('paths', 'temp', fallback='temp')
        elif hasattr(config, 'get') and 'APP_CONFIG' in config:
            temp_dir_str = config['APP_CONFIG'].get('paths', 'temp', fallback='temp')
        else:
            temp_dir_str = 'temp'
        self.temp_dir = Path(temp_dir_str)

    def get_audit_file_path(self, job_id: str) -> Path:
        return self.temp_dir / 'jobs' / job_id / 'review' / 'correction_audit.json'

    def append_event(self, event: CorrectionEvent):
        """Atomically appends an event to the job-local audit trail."""
        file_path = self.get_audit_file_path(event.job_id)
        
        events = self.get_events(event.job_id)
        events.append(event)
        
        # Write back safely
        temp_path = file_path.with_suffix('.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump([e.to_dict() for e in events], f, indent=2)
            
        temp_path.replace(file_path)

    def get_events(self, job_id: str) -> List[CorrectionEvent]:
        file_path = self.get_audit_file_path(job_id)
        if not file_path.exists():
            return []
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [CorrectionEvent.from_dict(d) for d in data]
        except Exception as e:
            logger.error(f"Failed to read audit events for {job_id}: {e}")
            return []

    def create_event(self, job_id: str, action: str, transaction_id: Optional[str] = None, **kwargs) -> CorrectionEvent:
        from app.models.correction import CorrectionAction
        event = CorrectionEvent(
            event_id=str(uuid.uuid4()),
            job_id=job_id,
            timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z",
            action=CorrectionAction(action),
            transaction_id=transaction_id,
            **kwargs
        )
        self.append_event(event)
        return event
