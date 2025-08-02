from unittest.mock import MagicMock, patch

import pytest

from helpers.base_ingestor import BaseIngestor, IngestorResult
from helpers.metadata_manager import ContentType


class TestIngestor(BaseIngestor):
    def get_content_type(self) -> ContentType:
        return ContentType.ARTICLE

    def get_module_name(self) -> str:
        return "test_ingestor"

    def fetch_content(self, source, metadata):
        if "error" in source:
            return False, "Test error"
        return True, "Test content"

    def process_content(self, content, metadata):
        return True


@pytest.fixture
def config(tmp_path):
    data_dir = tmp_path / "output"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "articles").mkdir(parents=True, exist_ok=True)
    (data_dir / "retries").mkdir(parents=True, exist_ok=True)
    return {
        "data_directory": str(data_dir),
        "article_output_path": str(data_dir / "articles"),
        "retry_queue_path": str(tmp_path / "retries" / "queue.jsonl"),
    }


@pytest.fixture
def ingestor(config):
    return TestIngestor(config)


def test_ingest_single_success(ingestor):
    result = ingestor.ingest_single("http://test.com/page")
    assert result.success
    assert result.metadata.title is None


def test_ingest_single_error(ingestor):
    result = ingestor.ingest_single("http://test.com/error")
    assert not result.success
    assert result.error == "Test error"


def test_batch_ingest(ingestor):
    sources = ["http://test.com/1", "http://test.com/2"]
    results = ingestor.ingest_batch(sources)
    assert len(results) == 2
    assert results["http://test.com/1"].success
    assert results["http://test.com/2"].success


@patch("helpers.base_ingestor.log_info")
def test_batch_ingest_logs(mock_log_info, ingestor):
    sources = ["http://test.com/1", "http://test.com/2"]
    ingestor.ingest_batch(sources)
    # Expect: 1 batch start + 2 successful ingestion logs + 1 completion log = 4 calls
    assert mock_log_info.call_count == 4


def test_handle_error_returns_bool(ingestor):
    # Test that handle_error returns a boolean and processes the error
    result = ingestor.handle_error("Test error", "http://test.com/error")
    assert isinstance(result, bool)
    # Error should be added to retry queue (we can see this in the queue.jsonl)
