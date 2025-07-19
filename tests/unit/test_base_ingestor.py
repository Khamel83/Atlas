import pytest
from unittest.mock import MagicMock, patch
from helpers.base_ingestor import BaseIngestor, IngestionResult

class TestIngestor(BaseIngestor):
    def __init__(self, config):
        super().__init__(config, 'test')

    def can_ingest(self, url):
        return "test.com" in url

    def ingest(self, url):
        if "error" in url:
            return IngestionResult(success=False, error_message="Test error")
        return IngestionResult(success=True, metadata={"title": "Test Title"})

@pytest.fixture
def config():
    return {
        "data_directory": "output",
        "test_output_path": "output/test",
    }

@pytest.fixture
def ingestor(config):
    return TestIngestor(config)

def test_can_ingest(ingestor):
    assert ingestor.can_ingest("http://test.com/page")
    assert not ingestor.can_ingest("http://example.com/page")

def test_ingest_success(ingestor):
    result = ingestor.ingest("http://test.com/page")
    assert result.success
    assert result.metadata["title"] == "Test Title"

def test_ingest_error(ingestor):
    result = ingestor.ingest("http://test.com/error")
    assert not result.success
    assert result.error_message == "Test error"

def test_batch_ingest(ingestor):
    urls = ["http://test.com/1", "http://test.com/2", "http://example.com/3"]
    results = ingestor.batch_ingest(urls)
    assert len(results) == 2
    assert results[0].success
    assert results[1].success