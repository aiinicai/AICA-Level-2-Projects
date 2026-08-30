import json
from pathlib import Path
from flask import current_app
from typing import Tuple, List, Optional
import logging

logger = logging.getLogger(__name__)

class BankDetector:
    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            # Try to resolve relative to app root
            try:
                root = Path(__file__).resolve().parent.parent.parent
                config_path = root / 'config' / 'bank_signatures.json'
            except RuntimeError: # outside app context
                config_path = Path('config/bank_signatures.json')
                
        self.banks = []
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.banks = data.get('banks', [])
            except Exception as e:
                logger.error(f"Failed to load bank signatures: {e}")
    
    def detect_bank(self, raw_text: str) -> Tuple[str, str, List[str]]:
        """
        Detects bank based on exact textual signatures in the raw text.
        Returns: (status, display_name, matched_signatures)
        """
        if not raw_text:
            return "unknown", "Unknown Bank", []
            
        text_upper = raw_text.upper()
        
        matches = []
        
        for bank in self.banks:
            for sig in bank.get('signatures', []):
                if sig.upper() in text_upper:
                    matches.append((bank['display_name'], sig))
                    
        # Find unique bank names matched
        unique_banks = list(set([m[0] for m in matches]))
        
        if len(unique_banks) == 0:
            return "unknown", "Unknown Bank", []
        elif len(unique_banks) == 1:
            matched_sigs = [m[1] for m in matches if m[0] == unique_banks[0]]
            return "detected", unique_banks[0], matched_sigs
        else:
            return "ambiguous", "Unknown Bank", [m[1] for m in matches]
