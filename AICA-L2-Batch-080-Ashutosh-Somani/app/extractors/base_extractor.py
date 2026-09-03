from abc import ABC, abstractmethod
from typing import Dict, Any
from app.models.extraction_result import ExtractionResult
import configparser

class BaseExtractor(ABC):
    """
    Abstract base class for all digital PDF extractors.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the identifier name of this extractor."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Returns the version string of the underlying engine."""
        pass
        
    @abstractmethod
    def can_handle(self, file_path: str, metadata: Dict[str, Any]) -> bool:
        """
        Determines if this extractor is suitable for the given PDF.
        """
        pass

    @abstractmethod
    def extract(self, job_id: str, file_path: str, config: configparser.ConfigParser) -> ExtractionResult:
        """
        Performs extraction and returns the unified ExtractionResult.
        """
        pass
