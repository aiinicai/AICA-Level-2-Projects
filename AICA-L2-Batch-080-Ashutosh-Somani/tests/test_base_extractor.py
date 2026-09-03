import pytest
from app.extractors.base_extractor import BaseExtractor
from app.models.extraction_result import ExtractionResult
import configparser

def test_base_extractor_interface():
    # Attempting to instantiate ABC directly should raise TypeError
    with pytest.raises(TypeError):
        BaseExtractor()
        
    class DummyExtractor(BaseExtractor):
        @property
        def name(self):
            return "dummy"
            
        @property
        def version(self):
            return "1.0"
            
        def can_handle(self, file_path, metadata):
            return True
            
        def extract(self, job_id, file_path, config):
            return ExtractionResult(
                job_id=job_id,
                extractor_used=self.name,
                extractor_version=self.version,
                status="success",
                page_count=1,
                pages_processed=1,
                total_words=0,
                total_characters=0,
                text_layer_status="none",
                table_candidate_count=0
            )
            
    extractor = DummyExtractor()
    assert extractor.name == "dummy"
    assert extractor.version == "1.0"
    
    res = extractor.extract("job1", "fake.pdf", configparser.ConfigParser())
    assert res.extractor_used == "dummy"
    assert res.text_layer_status == "none"
