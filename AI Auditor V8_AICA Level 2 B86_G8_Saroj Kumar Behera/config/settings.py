"""
AI Auditor V8 - Settings and User Configuration Management
"""

import os
import json
from dataclasses import dataclass, asdict
from config.constants import DEFAULT_VARIANCE_THRESHOLD, DEFAULT_MATERIALITY_THRESHOLD

SETTINGS_FILE = "ai_auditor_settings.json"

@dataclass
class AppSettings:
    variance_threshold: float = DEFAULT_VARIANCE_THRESHOLD
    materiality_threshold: float = DEFAULT_MATERIALITY_THRESHOLD
    default_unit: str = "₹ in Lakhs (1,00,000)"
    auto_detect_headings: bool = True
    enable_fuzzy_mapping: bool = True
    theme: str = "light"  # light, dark
    recent_files: list = None

    def __post_init__(self):
        if self.recent_files is None:
            self.recent_files = []

    def save(self, filepath: str = SETTINGS_FILE):
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    @classmethod
    def load(cls, filepath: str = SETTINGS_FILE) -> "AppSettings":
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return cls(**data)
            except Exception as e:
                print(f"Error loading settings, using defaults: {e}")
        return cls()
