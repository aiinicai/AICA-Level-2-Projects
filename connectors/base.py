"""
LexSecure India Pro - Base Regulatory Connector Engine
Abstract interface for Statutory Notification & Gazette Feed Ingestion
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseRegulatoryConnector(ABC):
    """
    Abstract Base Class for Indian Regulatory Ingestion Connectors.
    All connectors (RSS, API, Scraping, Manual) inherit from this interface.
    """

    def __init__(self, name: str, statutory_body: str):
        self.name = name
        self.statutory_body = statutory_body  # e.g. MCA, RBI_FEMA, LABOUR_MINISTRY, DPDPB, CERT_IN

    @abstractmethod
    def fetch_updates(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetches latest regulatory circulars/notifications.
        Returns list of standardized circular dictionaries.
        """
        pass

    @abstractmethod
    def parse_circular(self, raw_content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes unstructured gazette/circular text into structured data:
        - title
        - circular_number
        - official_date
        - raw_text
        - severity (CRITICAL, HIGH, ADVISORY)
        - source_url
        """
        pass

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """
        Tests the endpoint/source connectivity.
        Returns {'status': 'OK'|'ERROR', 'message': str}
        """
        pass
