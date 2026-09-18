from typing import List, Optional

from reconai.models.transaction import LedgerEntry, AuditFlag
from reconai.config import AppConfig
from reconai.audit.rules_engine import AuditRulesEngine
from reconai.audit.ai_flagger import AIFlagger


class AuditManager:
    """Orchestrates comprehensive expense and compliance auditing."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig()
        self.rules_engine = AuditRulesEngine(self.config.audit)
        self.ai_flagger = AIFlagger(self.config.audit, self.config.reconciliation)

    def run_audit(self, entries: List[LedgerEntry]) -> List[AuditFlag]:
        flags: List[AuditFlag] = []

        # 1. Deterministic Rule Checks
        deterministic_flags = self.rules_engine.audit(entries)
        flags.extend(deterministic_flags)

        # 2. AI / Semantic Checks
        ai_flags = self.ai_flagger.audit(entries)
        flags.extend(ai_flags)

        # Sort flags by severity (HIGH -> MEDIUM -> LOW -> INFO)
        severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}
        flags.sort(key=lambda f: severity_order.get(f.severity.value, 4))

        return flags
