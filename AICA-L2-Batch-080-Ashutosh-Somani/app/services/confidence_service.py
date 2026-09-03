from typing import List
from app.models.exception import ExceptionRecord

class ConfidenceService:
    """
    Transparent rule-based heuristic scoring (0-100) for transaction validation.
    This is NOT a statistical probability.
    """
    
    @staticmethod
    def calculate_score(exceptions: List[ExceptionRecord], is_structurally_valid: bool, is_balance_verified: bool) -> int:
        has_critical = any(e.severity == "CRITICAL" for e in exceptions)
        has_error = any(e.severity == "ERROR" for e in exceptions)
        has_warning = any(e.severity == "WARNING" for e in exceptions)
        
        # Severe structural or math errors
        if not is_structurally_valid or has_critical:
            return 20
            
        if has_error:
            # Contains financial mismatches or ambiguities
            return 40
            
        if is_balance_verified and not has_warning:
            # Verified perfectly with exact math and zero exceptions
            return 100
            
        if not is_balance_verified and not has_warning:
            # E.g. Missing prior balance, but row looks completely fine structurally
            return 90
            
        if has_warning:
            # E.g. Missing transaction balance, possible duplicate, or date warning
            return 70
            
        return 50 # Fallback
