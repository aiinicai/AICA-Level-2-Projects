"""
LexSecure India Pro - Manual Circular & Gazette Uploader Connector
Accepts manual PDF / Text uploads of internal or external legal circulars
"""

from datetime import datetime
from typing import List, Dict, Any
from .base import BaseRegulatoryConnector

class ManualCircularConnector(BaseRegulatoryConnector):
    """
    Handles uploaded internal company circulars, state gazettes, and ad-hoc notifications.
    """

    def __init__(self):
        super().__init__(name="Manual & Internal Legal Gazette Intake", statutory_body="MCA")

    def test_connection(self) -> Dict[str, Any]:
        return {
            "status": "OK",
            "message": "Manual Gazette & Circular Intake Ready"
        }

    def fetch_updates(self, limit: int = 10) -> List[Dict[str, Any]]:
        return []

    def parse_circular(self, raw_content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        # Clean text and extract key metadata fields
        statutory_body = metadata.get("statutory_body", "MCA")
        title = metadata.get("title", "Ad-hoc Regulatory Circular")
        circular_number = metadata.get("circular_number", f"MANUAL/{datetime.now().strftime('%Y%m%d')}/01")
        official_date = metadata.get("official_date", datetime.now().strftime("%Y-%m-%d"))
        severity = metadata.get("severity", "HIGH")
        source_url = metadata.get("source_url", "Internal Intake")

        return {
            "statutory_body": statutory_body,
            "title": title,
            "circular_number": circular_number,
            "official_date": official_date,
            "raw_text": raw_content.strip(),
            "severity": severity,
            "source_url": source_url
        }
